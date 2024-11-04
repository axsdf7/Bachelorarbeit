import socket
import threading
import time
import subprocess
import re
import logging
import os


def create_logger():
    # Log-Datei entfernen, falls sie existiert
    if os.path.exists('p2p.log'):
        os.remove('p2p.log')

    # Logger konfigurieren
    logging.basicConfig(
        handlers=[
            logging.FileHandler('p2p.log'),
            logging.StreamHandler()
        ],
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s')

    return logging.getLogger("p2pLogger")


def get_ip_address(interface="wlan0"):
    try:
        # Führe 'ip addr show [Interface]' aus
        result = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)

        # Überprüfe die Ausgabe mit einem regulären Ausdruck, um die IP-Adresse zu finden
        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)

        # Wenn eine IP-Adresse gefunden wurde, gib sie zurück
        if ip_match:
            return ip_match.group(1)
        else:
            print("Keine IP-Adresse gefunden.")
            return None
    except Exception as e:
        print(f"Fehler: {e}")
        return None


def broadcast_own_ip(logging_object, socket_object, broadcast_address, broadcast_port, ip_address):
    while True:
        try:
            message = f"{ip_address}"
            socket_object.sendto(message.encode(), (broadcast_address, broadcast_port))
            logging_object.info(f"Sende eigene IPv4 {message} per Broadcast...")
        except Exception as e:
            logging_object.info(f"Fehler: {e}")
        time.sleep(5)


def listen_for_peers(logging_object, socket_object, peer_ips, ip_address, timeout):
    # Lock zur Vermeidung von Deadlocks
    peer_ips_lock = threading.Lock()
    # Lauscht auf eingehende Nachrichten und fügt IP-Adressen anderer Teilnehmer zur Liste hinzu.
    while True:
        try:
            data, addr = socket_object.recvfrom(1024)
            peer_ip = data.decode().strip()  # Die empfangene IP-Adresse aus der Nachricht extrahieren
            current_time = time.time()
            peer_found = False
            # Check ob IP schon in Liste und aktualisiert Zeitstempel
            for peer in peer_ips:
                if peer["ip"] == peer_ip:
                    with peer_ips_lock:
                        peer["last_seen"] = current_time
                        peer_found = True
            # Falls IP nicht in Liste, dann hinzufuegen
            if not peer_found and peer_ip != ip_address:
                with peer_ips_lock:
                    peer_ips.append({"ip": peer_ip, "last_seen": current_time})
                    logging_object.info(f"Neuer Teilnehmer entdeckt: {peer_ip}")
            # IPs entfernen, wenn Timeout erreicht
            with peer_ips_lock:
                peer_ips[:] = [peer for peer in peer_ips if current_time - peer["last_seen"] <= timeout]
        except Exception as e:
            logging_object.info(f"Fehler beim Empfangen: {e}")


def send_data(logging_object, ip_address, socket_object, peer_ips, port, frequency):
    # Sendet provisorische Daten mit einer vorgegebenen Frequenz
    counter = 0
    period_duration = 1 / frequency
    try:
        while True:
            message = f"{ip_address}: {str(counter)}"
            for peer_ip in peer_ips:
                if not ip_address == peer_ip:
                    socket_object.sendto(message.encode(), (peer_ip["ip"], port))
                    logging_object.info(f"Nachricht gesendet an {peer_ip['ip']}: {message}")
            counter += 1
            time.sleep(period_duration)
    except KeyboardInterrupt:
        logging_object.info("Übertragung manuell abgebrochen.")


def receive_data(logging_object, socket_object):
    # Empfängt Daten vom Server_Library.
    try:
        while True:
            data = socket_object.recv(1024).decode()
            if data:
                logging_object.info(f"Nachricht empfangen: {data}")
            else:
                logging_object.info("Verbindung zum Netzwerk beendet.")
                break
    except KeyboardInterrupt:
        logging_object.info("Empfang manuell abgebrochen.")


def start_node(logging_object, frequency, broadcast_address, broadcast_port, communication_port):

    # Timeout fuer Liste
    timeout = 15

    # finde IP-Adresse des Geräts
    ipv4 = get_ip_address()

    # Liste mit Teilnehmern
    peer_list = []

    # Broadcast Socket Objekt
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_sock.bind(("", broadcast_port))

    # Sender Socket Objekt
    sending_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Empfaenger Socket Objekt
    receiving_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiving_socket.bind(("", communication_port))

    # Threads initialisieren
    broadcast_thread = threading.Thread(target=broadcast_own_ip,
                                        args=(logging_object, broadcast_sock, broadcast_address, broadcast_port, ipv4))
    broadcast_thread.daemon = True

    listener_thread = threading.Thread(target=listen_for_peers,
                                       args=(logging_object, broadcast_sock, peer_list, ipv4, timeout))
    listener_thread.daemon = True

    send_thread = threading.Thread(target=send_data,
                                   args=(logging_object, ipv4, sending_socket, peer_list,
                                         communication_port, frequency))
    receive_thread = threading.Thread(target=receive_data,
                                      args=(logging_object, receiving_socket))

    # Threads starten
    broadcast_thread.start()
    listener_thread.start()
    send_thread.start()
    receive_thread.start()

    send_thread.join()
    receive_thread.join()

    broadcast_sock.close()
    sending_socket.close()
    receiving_socket.close()


# Start
send_freq = 10
bc_address = "192.168.2.255"
bc_port = 5005
c_port = 5006

logger = create_logger()

start_node(logger, send_freq, bc_address, bc_port, c_port)

import socket
import threading
import time
import subprocess
import re
import logging
import os

"""*****************************************************************************************************************"""


def send_data(logging_object: logging.Logger, ip_address: str, socket_object: socket.socket,
              peer_list: list, port: int, frequency: int):
    """
    Sendet Daten an andere Teilnehmer mit gegebener Frequenz.
    :param logging_object: Logger des Geräts
    :param ip_address: Statische IPv4 des Geräts im Mesh-Netzwerk
    :param socket_object: Sender-Socket des Geräts
    :param peer_list: 2D Liste mit IPs und Zeitstempel aller Teilnehmer
    :param port: Port zur Kommunikation
    :param frequency: Frequenz für Nachrichtenübertragung in Hz
    :return: None
    """
    counter = 0
    period_duration = 1 / frequency
    try:
        while True:
            message = f"{ip_address}: {str(counter)}"
            for peer in peer_list:
                if not ip_address == peer['ip']:
                    socket_object.sendto(message.encode(), (peer["ip"], port))
                    logging_object.info(f"Nachricht gesendet an {peer['ip']}: {message}")
            counter += 1
            time.sleep(period_duration)
    except KeyboardInterrupt:
        logging_object.info("Übertragung manuell abgebrochen.")
    except Exception as e:
        logging_object.info(f"Error: {e}")


def receive_data(logging_object: logging.Logger, socket_object: socket.socket):
    """
    Empfängt Daten von anderen Teilnehmern.
    :param logging_object: Logger des Geräts
    :param socket_object: Empfänger-Socket des Geräts
    :return: None
    """
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
    except Exception as e:
        logging_object.info(f"Error: {e}")


"""*****************************************************************************************************************"""


def create_logger(name: str):
    """
    Erstellt einen neuen Logger, löscht die alte Log-Datei und gibt Logger-Objekt zurück.
    :param name: Name der Log-datei
    :return: Logger-Objekt
    """
    # Log-Datei entfernen, falls sie existiert
    if os.path.exists(name):
        os.remove(name)

    # Logger konfigurieren
    logging.basicConfig(
        handlers=[
            logging.FileHandler(name),
            logging.StreamHandler()
        ],
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s')

    return logging.getLogger(name)


def get_ip_address(interface="wlan0"):
    """
    Gibt die statische IPv4 des Geräts im Mesh-Netzwerk zurück.
    :param interface: Schnittstelle für Mesh-Netzwerk, standardmäßig wlan0
    :return: IPv4
    """
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


def broadcast_own_ip(logging_object: logging.Logger, socket_object: socket.socket, broadcast_address: str,
                     broadcast_port: int, ip_address: str, interval: int):
    """
    Sendet eigene IPv4 per Broadcast an alle Teilnehmer.
    :param logging_object: Logger des Geräts
    :param socket_object: Verbindung des Geräts mit Broadcast-Kanal
    :param broadcast_address: IPv4 des Broadcast-Kanals
    :param broadcast_port: Port des Broadcast-Kanals
    :param ip_address: IPv4 des Geräts
    :param interval: Sendeintervall der Broadcast-Nachricht
    :return: None
    """
    while True:
        try:
            message = f"{ip_address}"
            socket_object.sendto(message.encode(), (broadcast_address, broadcast_port))
            logging_object.info(f"Sende eigene IPv4 {message} per Broadcast...")
        except Exception as e:
            logging_object.info(f"Fehler: {e}")
        time.sleep(interval)


def listen_for_peers(logging_object: logging.Logger, socket_object: socket.socket, peer_list: list,
                     ip_address: str, timeout: int):
    """
    Lauscht auf dem Broadcast-Kanal, sucht nach anderen Teilnehmern und fügt diese der Liste peer_list zu.
    :param logging_object: Logger des Geräts
    :param socket_object: Verbindung des Geräts mit Broadcast-Kanal
    :param peer_list: 2D Liste mit IPs und Zeitstempel aller Teilnehmer
    :param ip_address: IPv4 des Geräts
    :param timeout: Dauer, bis ein Gerät ohne Rückmeldung aus der Liste peer_list entfernt wird
    :return: None
    """
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
            for peer in peer_list:
                if peer["ip"] == peer_ip:
                    with peer_ips_lock:
                        peer["last_seen"] = current_time
                        peer_found = True
            # Falls IP nicht in Liste, dann hinzufuegen
            if not peer_found and peer_ip != ip_address:
                with peer_ips_lock:
                    peer_list.append({"ip": peer_ip, "last_seen": current_time})
                    logging_object.info(f"Neuer Teilnehmer entdeckt: {peer_ip}")
            # IPs entfernen, wenn Timeout erreicht
            with peer_ips_lock:
                peer_list[:] = [peer for peer in peer_list if current_time - peer["last_seen"] <= timeout]
        except Exception as e:
            logging_object.info(f"Fehler beim Empfangen: {e}")


def start(logging_object: logging.Logger, frequency: int, communication_port: int, timeout: int, bc_interval: int):
    """
    Startet den Teilnehmer.
    :param logging_object: Logger des Geräts
    :param frequency: Frequenz der Nachrichtenübertragung
    :param communication_port: Port der Kommunikation
    :param timeout: Dauer, bis ein Gerät ohne Rückmeldung aus der Liste peer_list entfernt wird
    :param bc_interval: Sendeintervall der Broadcast-Nachricht
    :return: None
    """

    # Broadcast Setup
    broadcast_address = "192.168.2.255"
    broadcast_port = 5005

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
                                        args=(logging_object, broadcast_sock, broadcast_address,
                                              broadcast_port, ipv4, bc_interval))
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

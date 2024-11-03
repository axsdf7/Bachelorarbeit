import socket
import threading
import time
import subprocess
import re


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


def broadcast_own_ip(socket_object, broadcast_address, broadcast_port, ip_address):

    while True:
        try:
            message = f"{ip_address}"
            socket_object.sendto(message.encode(), (broadcast_address, broadcast_port))
            print(f"Sende eigene IPv4 {message} per Broadcast...")
        except Exception as e:
            print(f"Fehler: {e}")
        time.sleep(2)


def listen_for_peers(socket_object, peer_ips, ip_address):
    # Lauscht auf eingehende Nachrichten und fügt IP-Adressen anderer Teilnehmer zur Liste hinzu.
    while True:
        try:
            data, addr = socket_object.recvfrom(1024)
            peer_ip = data.decode().strip()  # Die empfangene IP-Adresse aus der Nachricht extrahieren
            if peer_ip not in peer_ips and peer_ip != ip_address:
                peer_ips.add(peer_ip)
                print(f"Neuer Teilnehmer entdeckt: {peer_ip}")
        except Exception as e:
            print(f"Fehler beim Empfangen: {e}")


def send_data(ip_address, socket_object, peer_ips, port, frequency):
    # Sendet Daten mit einem Zähler alle 50 ms an den Server.
    counter = 0
    period_duration = 1 / frequency
    try:
        while True:
            message = f"{ip_address}: {str(counter)}"
            for peer_ip in peer_ips:
                if not ip_address == peer_ip:
                    socket_object.sendto(message.encode(), (peer_ip, port))
                    print(f"Nachricht gesendet an {peer_ip}: {message}")
            counter += 1
            time.sleep(period_duration)
    except KeyboardInterrupt:
        print("Übertragung manuell abgebrochen.")


def receive_data(socket_object):
    # Empfängt Daten vom Server.
    try:
        while True:
            data = socket_object.recv(1024).decode()
            if data:
                print("Nachricht empfangen:", data)
            else:
                print("Verbindung zum Netzwerk beendet.")
                break
    except KeyboardInterrupt:
        print("Empfang manuell abgebrochen.")


def start_node(frequency, broadcast_address, broadcast_port, communication_port):

    # finde IP-Adresse des Geräts
    ipv4 = get_ip_address()

    # Liste mit Teilnehmern
    peer_list = set()

    # Broadcast socket objekt
    broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    broadcast_sock.bind(("", broadcast_port))

    sending_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    receiving_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiving_socket.bind(("", communication_port))

    broadcast_thread = threading.Thread(target=broadcast_own_ip,
                                        args=(broadcast_sock, broadcast_address, broadcast_port, ipv4))
    broadcast_thread.daemon = True

    listener_thread = threading.Thread(target=listen_for_peers,
                                       args=(broadcast_sock, peer_list, ipv4))
    listener_thread.daemon = True

    send_thread = threading.Thread(target=send_data,
                                   args=(ipv4, sending_socket, peer_list, communication_port, frequency))
    receive_thread = threading.Thread(target=receive_data,
                                      args=(receiving_socket,))

    broadcast_thread.start()
    listener_thread.start()
    send_thread.start()
    receive_thread.start()

    send_thread.join()
    receive_thread.join()

    broadcast_sock.close()


# Start
freq = 1
bc_address = "192.168.2.255"
bc_port = 5005
c_port = 5006
start_node(freq, bc_address, bc_port, c_port)

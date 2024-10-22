import socket
import threading
import logging
import time
import os
import psutil  # Modul für den Zugriff auf Netzwerkinterfaces


def create_logger():
    # Log-Datei entfernen, falls sie existiert
    if os.path.exists('server.log'):
        os.remove('server.log')

    # Logger konfigurieren
    logging.basicConfig(
        handlers=[
            logging.FileHandler('server.log'),
            logging.StreamHandler()
        ],
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s')

    return logging.getLogger("ServerLogger")


def broadcast_server_info(logging_object, port_server, port_broadcast, server_ip):
    interval = 5
    # Sendet die IP-Adresse des Servers regelmäßig per Broadcast
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"{server_ip}:{port_server}"
        while True:
            sock.sendto(message.encode(), ('<broadcast>', port_broadcast))
            logging_object.info(f"Broadcast Nachricht gesendet: {message}")
            time.sleep(interval)


def get_localip(logging_object):
    timeout = 60
    interval = 1
    # Versucht eine gültige lokale IP-Adresse zu finden, andernfalls wird der Server heruntergefahren
    start_time = time.time()

    while time.time() - start_time < timeout:
        for [_, addrs] in psutil.net_if_addrs().items():
            for addr in addrs:
                # Prüft auf IPv4-Adresse, die nicht die Loopback-Adresse ist
                if addr.family == socket.AF_INET and addr.address != "127.0.0.1":
                    logging_object.info(f"Gefundene lokale IP-Adresse: {addr.address}")
                    return addr.address

        # Eine Sekunde warten, bevor erneut gesucht wird
        time.sleep(interval)

    # Timeout erreicht, keine gültige IP-Adresse gefunden
    logging_object.error("Fehler: Keine gültige IP-Adresse gefunden. Server wird heruntergefahren.")
    raise SystemExit("Server heruntergefahren: Keine gültige IP-Adresse gefunden.")


# Funktion zum Empfang von Nachrichten vom Client
def receive_from_client(logging_object, client_socket, address):
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if data:
                logging_object.info(f"Empfangene Nachricht von {address}: {data}")
            else:
                logging_object.info(f"Verbindung mit {address} geschlossen.")
                break
    except ConnectionResetError:
        logging_object.info(f"Verbindung mit {address} unerwartet getrennt.")


# Funktion zum Senden von Nachrichten an den Client
def send_to_client(logging_object, client_socket, address):
    counter = 0
    try:
        while True:
            message = f"Server Nachricht {counter}"
            client_socket.sendall(message.encode())
            logging_object.info(f"Nachricht an {address} gesendet: {message}")
            counter += 1
            time.sleep(0.05)
            if counter > 100:
                break
    except ConnectionResetError:
        logging_object.info(f"Verbindung mit {address} zum Senden getrennt.")


def handle_client(logging_object, client_socket, addr):
    # Verarbeitet eingehende und ausgehende Nachrichten mit dem Client

    logging_object.info(f"Verbindung hergestellt mit {addr}")

    # Erstelle und starte die Threads für Senden und Empfangen
    receive_thread = threading.Thread(target=receive_from_client, args=(logging_object, client_socket, addr))
    send_thread = threading.Thread(target=send_to_client, args=(logging_object, client_socket, addr))
    receive_thread.start()
    send_thread.start()

    # Warte, bis beide Threads beendet sind
    receive_thread.join()
    send_thread.join()

    client_socket.close()


def start_server(logging_object, port_server, port_broadcast):
    server_ip = get_localip(logging_object)

    # Erstelle server_socket Objekt
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_ip, port_server))
    server_socket.listen(5)
    logging_object.info(f"Server läuft auf {server_ip}:{port_server} und wartet auf Verbindungen...")

    # Startet den Broadcast-Thread
    broadcast_thread = threading.Thread(target=broadcast_server_info, args=(logging_object, port_server, port_broadcast, server_ip))
    broadcast_thread.daemon = True
    broadcast_thread.start()

    try:
        while True:
            client_socket, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(logging_object, client_socket, addr))
            client_thread.start()
            logging_object.info(f"Thread für Verbindung mit {addr} gestartet.")
    except KeyboardInterrupt:
        logging_object.info("Server wird heruntergefahren.")
    finally:
        server_socket.close()


# Starte den Server
server_port = 50000
broadcast_port = 50001
logger = create_logger()
start_server(logger, server_port, broadcast_port)

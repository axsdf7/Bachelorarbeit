import socket
import threading
import logging
import time
import os
import psutil  # Modul für den Zugriff auf Netzwerkinterfaces


clients = []  # Liste aller verbundenen Clients


def create_logger():
    # Log-Datei entfernen, falls sie existiert
    if os.path.exists('server.log'):
        os.remove('server.log')

    # Logger konfigurieren
    logging.basicConfig(
        filename='server.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s')

    return logging.getLogger("ServerLogger")


def broadcast_server_info(port_server, port_broadcast, server_ip, interval=5):
    # Sendet die IP-Adresse des Servers regelmäßig per Broadcast
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"{server_ip}:{port_server}"
        while True:
            sock.sendto(message.encode(), ('<broadcast>', port_broadcast))
            logger.info(f"Broadcast Nachricht gesendet: {message}")
            time.sleep(interval)


def get_localip(timeout=60):
    # Versucht eine gültige lokale IP-Adresse zu finden, andernfalls wird der Server heruntergefahren
    start_time = time.time()

    while time.time() - start_time < timeout:
        for [_, addrs] in psutil.net_if_addrs().items():
            for addr in addrs:
                # Prüft auf IPv4-Adresse, die nicht die Loopback-Adresse ist
                if addr.family == socket.AF_INET and addr.address != "127.0.0.1":
                    logger.info(f"Gefundene lokale IP-Adresse: {addr.address}")
                    return addr.address

        # Eine Sekunde warten, bevor erneut gesucht wird
        time.sleep(1)

    # Timeout erreicht, keine gültige IP-Adresse gefunden
    logger.error("Fehler: Keine gültige IP-Adresse gefunden. Server wird heruntergefahren.")
    raise SystemExit("Server heruntergefahren: Keine gültige IP-Adresse gefunden.")


# Funktion zum Empfang von Nachrichten vom Client
def receive_from_client(client_socket, address):
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if data:
                logger.info(f"Empfangene Nachricht von {address}: {data}")
            else:
                logger.info(f"Verbindung mit {address} geschlossen.")
                break
    except ConnectionResetError:
        logger.info(f"Verbindung mit {address} unerwartet getrennt.")


# Funktion zum Senden von Nachrichten an den Client
def send_to_clients(data, sender_socket):
    for client in clients:
        if client != sender_socket:
            client.sendall(data.encode())


def handle_client(client_socket, client_address):
    logger.info(f"Neue Verbindung von {client_address}")
    clients.append(client_socket)

    with open('client_data.log', 'a') as f:  # Datei zum Speichern der empfangenen Daten
        try:
            while True:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                logger.info(f"Empfangene Nachricht von {client_address}: {data}")
                f.write(f"{client_address}: {data}\n")
                f.flush()  # Daten sofort in die Datei schreiben
                send_to_clients(data, client_socket)
        finally:
            clients.remove(client_socket)
            logger.info(f"Verbindung beendet: {client_address}")
            client_socket.close()


def start_server(port_server, port_broadcast):
    server_ip = get_localip()
    # Startet den Broadcast-Thread
    broadcast_thread = threading.Thread(target=broadcast_server_info(port_server, port_broadcast, server_ip))
    broadcast_thread.daemon = True
    broadcast_thread.start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_ip, port_server))
    server_socket.listen(5)
    logger.info(f"Server läuft auf {server_ip}:{port_server} und wartet auf Verbindungen...")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client(client_socket, addr))
            client_thread.start()
            logger.info(f"Thread für Verbindung mit {addr} gestartet.")
    except KeyboardInterrupt:
        logger.info("Server wird heruntergefahren.")
    finally:
        server_socket.close()


# Starte den Server
server_port = 50000
broadcast_port = 50001
logger = create_logger()
start_server(server_port, broadcast_port)

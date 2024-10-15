import socket
import threading
import logging
import time
import os
import psutil  # Modul für den Zugriff auf Netzwerkinterfaces

# Log-Datei entfernen, falls sie existiert
log_file = 'server.log'
if os.path.exists(log_file):
    os.remove(log_file)

# Logger konfigurieren
logging.basicConfig(
    filename='server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ServerLogger")

def broadcast_server_info(server_port=50000, broadcast_port=50001, interval=5):
    """Sendet die IP-Adresse des Servers regelmäßig per Broadcast"""
    server_ip = get_localip()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"{server_ip}:{server_port}"
        while True:
            sock.sendto(message.encode(), ('<broadcast>', broadcast_port))
            logger.info(f"Broadcast Nachricht gesendet: {message}")
            time.sleep(interval)

def get_localip(timeout=60):
    # Versucht eine gültige lokale IP-Adresse zu finden, andernfalls wird der Server heruntergefahren
    start_time = time.time()

    while time.time() - start_time < timeout:
        for interface, addrs in psutil.net_if_addrs().items():
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


def handle_client(client_socket, addr):
    """Verarbeitet eingehende und ausgehende Nachrichten mit dem Client"""

    logger.info(f"Verbindung hergestellt mit {addr}")

    # Funktion zum Empfang von Nachrichten vom Client
    def receive_from_client():
        try:
            while True:
                data = client_socket.recv(1024).decode()
                if data:
                    logger.info(f"Empfangene Nachricht von {addr}: {data}")
                else:
                    logger.info(f"Verbindung mit {addr} geschlossen.")
                    break
        except ConnectionResetError:
            logger.info(f"Verbindung mit {addr} unerwartet getrennt.")

    # Funktion zum Senden von Nachrichten an den Client
    def send_to_client():
        counter = 0
        try:
            while True:
                message = f"Server Nachricht {counter}"
                client_socket.sendall(message.encode())
                logger.info(f"Nachricht an {addr} gesendet: {message}")
                counter += 1
                time.sleep(0.1)  # Sendet jede Sekunde eine Nachricht
                if counter > 100:
                    break
        except ConnectionResetError:
            logger.info(f"Verbindung mit {addr} zum Senden getrennt.")

    # Erstelle und starte die Threads für Senden und Empfangen
    receive_thread = threading.Thread(target=receive_from_client)
    send_thread = threading.Thread(target=send_to_client)
    receive_thread.start()
    send_thread.start()

    # Warte, bis beide Threads beendet sind
    receive_thread.join()
    send_thread.join()

    client_socket.close()

def start_server(port=50000):
    # Startet den Broadcast-Thread
    broadcast_thread = threading.Thread(target=broadcast_server_info)
    broadcast_thread.daemon = True
    broadcast_thread.start()

    server_ip = get_localip()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_ip, port))
    server_socket.listen(5)
    logger.info(f"Server läuft auf {server_ip}:{port} und wartet auf Verbindungen...")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            client_thread.start()
            logger.info(f"Thread für Verbindung mit {addr} gestartet.")
    except KeyboardInterrupt:
        logger.info("Server wird heruntergefahren.")
    finally:
        server_socket.close()

# Starte den Server
start_server()


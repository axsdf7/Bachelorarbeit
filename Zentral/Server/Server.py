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
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ServerLogger")


def broadcast_server_info(server_port=50000, broadcast_port=50001, interval=5):
    # Sendet die IP-Adresse des Servers regelmäßig per Broadcast (HIER: UDP, SOCK_GRAM)
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
    # Funktion zur Handhabung einer einzelnen Client-Verbindung
    logger.info(f"Verbindung hergestellt mit {addr}")

    # Nachrichten vom Client empfangen, bis die Verbindung geschlossen wird
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if not data:
                logger.info(f"Verbindung mit {addr} geschlossen.")
                break
            logger.info(f"Empfangene Nachricht von {addr}: {data}")
    finally:
        client_socket.close()


def start_server(port=50000):
    # Startet den Broadcast-Thread
    broadcast_thread = threading.Thread(target=broadcast_server_info)
    broadcast_thread.daemon = True  # Thread beendet sich mit dem Hauptprogramm
    broadcast_thread.start()
    # Finde Hostname und IP des Servers heraus
    server_ip = get_localip()
    # SOCK_STREAM: TCP/IP, SOCK_DGRAM: UDP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_ip, port))
    # Erlaubt bis zu 5 eingehende Verbindungen gleichzeitig
    server_socket.listen(5)
    logger.info(f"Server läuft auf {server_ip}:{port} und wartet auf Verbindungen...")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            # Ein neuer Thread wird für jede Client-Verbindung erstellt
            client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            client_thread.start()
            logger.info(f"Thread für Verbindung mit {addr} gestartet.")
    except KeyboardInterrupt:
        logger.info("Server wird heruntergefahren...")

    finally:
        server_socket.close()


# Starte den Server
start_server()

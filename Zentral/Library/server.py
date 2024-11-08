import socket
import threading
import logging
import time
import os
import psutil  # Modul für den Zugriff auf Netzwerkinterfaces


"""*****************************************************************************************************************"""


def send_to_clients(logging_object: logging.Logger, data: str, clients_set: set, client_socket: socket.socket):
    """
    Funktion, die bei Verbindung eines Clients A mit dem Server aufgerufen wird und die Daten des Clients A an alle
    anderen Clients aus clients_list schickt.
    :param logging_object: Logger, um Nachrichten vom Server an Clients zu speichern
    :param data: Daten eines Clients, die gesendet werden sollen
    :param clients_set: Set aller Clients inklusive Client A
    :param client_socket: Verbindung zwischen Server und Client A
    :return: None
    """
    for client in clients_set:
        if client != client_socket:
            client.sendall(data.encode())
            logging_object.info(f"Nachricht an {client.getpeername()} von {client_socket.getpeername()} {data}")


def receive_from_client(logging_object: logging.Logger, client_socket: socket.socket, address: str):
    """
    Funktion, die bei Verbindung eines Clients A mit dem Server aufgerufen wird und die Daten des Clients A empfängt
    und zurückgibt.
    :param logging_object: Logger des Servers, um Kommunikation zwischen Client und Server zu speichern
    :param client_socket: Verbindung zwischen Server und Client A
    :param address: IPv4 und Port des Clients
    :return: data
    """
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if data:
                logging_object.info(f"Empfangene Nachricht von {address}: {data}")
                return data
            else:
                logging_object.info(f"Verbindung mit {address} geschlossen.")
                break
    except ConnectionResetError:
        logging_object.info(f"Verbindung mit {address} unerwartet getrennt.")


"""*****************************************************************************************************************"""


def create_logger(name: str):
    """
    Erstellt einen neuen Logger, löscht die alte Log-Datei und gibt Logger-Objekt zurück.
    :param name: Name der Log-datei
    :return: Logger-Objekt
    """
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


def broadcast_server_info(logging_object: logging.Logger, port_server: int,
                          port_broadcast: int, server_ip: str, interval:  int):
    """
    Sendet periodisch alle *interval* Sekunden eine Broadcast-Nachricht an alle Teilnehmer mit IPv4 und Port des
    Servers.
    :param logging_object: Logger des Servers
    :param port_server: Port des Servers für Kommunikation
    :param port_broadcast: Port des Servers für Broadcasting
    :param server_ip: IPv4 des Servers
    :param interval: Sendeintervall der Broadcast-Nachricht
    :return: None
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    message = f"{server_ip}:{port_server}"
    while True:
        sock.sendto(message.encode(), ('<broadcast>', port_broadcast))
        logging_object.info(f"Broadcast Nachricht gesendet: {message}")
        time.sleep(interval)


def get_localip(logging_object: logging.Logger) -> str:
    """
    Gibt die IPv4 des Servers im lokalen Netzwerk zurück.
    :param logging_object: Logger des Servers
    :return: IPv4 des Geräts
    """
    timeout = 30
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

        # [interval] warten, bevor erneut gesucht wird
        time.sleep(interval)

    # Timeout erreicht, keine gültige IP-Adresse gefunden
    logging_object.error("Fehler: Keine gültige IP-Adresse gefunden. Server wird heruntergefahren.")
    raise SystemExit("Server heruntergefahren: Keine gültige IP-Adresse gefunden.\n"
                     "Überprüfen Sie die Verbindung mit dem Router.")


def handle_client(server_logging_object: logging.Logger, clients_set: set,
                  client_socket: socket.socket, client_address: str):
    """
    Bearbeitet das Senden und Empfangen von Nachrichten eines Clients.
    :param server_logging_object: Logger des Servers
    :param clients_set: Set aller Clients inklusive Client A
    :param client_socket: Verbindung zwischen Server und Client A
    :param client_address: Adresse des Clients A, welcher data sendet
    :return: None
    """
    server_logging_object.info(f"Neue Verbindung von {client_address}")
    clients_set.add(client_socket)

    try:
        while True:
            data = receive_from_client(server_logging_object, client_socket, client_address)
            if not data:
                break
            else:
                send_to_clients(server_logging_object, data, clients_set, client_socket)
    finally:
        clients_set.remove(client_socket)
        server_logging_object.info(f"Verbindung beendet mit {client_address}")
        client_socket.close()


def start(logging_object: logging.Logger, port_server: int, port_broadcast: int, interval_broadcast: int):
    """
    Startet den Server. Wartet auf eingehende Verbindungen und erstellt pro Verbindung einen Thread mit
    handle_client().
    :param logging_object: Logger des Servers
    :param port_server: Port des Servers für Client-Kommunikation
    :param port_broadcast: Port für Broadcast-kommunikation
    :param interval_broadcast: Intervall der Broadcast-Nachrichten
    :return: None
    """
    server_ip = get_localip(logging_object)
    clients = set()

    if server_ip:
        # Erstelle server_socket Objekt in TCP-Konfiguration
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((server_ip, port_server))
        server_socket.listen(250)
        logging_object.info(f"Server läuft auf {server_ip}:{port_server} und wartet auf Verbindungen...")

        # Startet den Broadcast-Thread
        broadcast_thread = threading.Thread(
            target=broadcast_server_info,
            args=(logging_object, port_server, port_broadcast, server_ip, interval_broadcast))
        broadcast_thread.daemon = True
        broadcast_thread.start()

        # Starte den Client-Handler pro eingegangene Verbindung
        try:
            while True:
                client_socket, client_address = server_socket.accept()
                # Startet einen Thread pro Client
                client_thread = threading.Thread(target=handle_client,
                                                 args=(logging_object, clients, client_socket, client_address))
                client_thread.start()
                logging_object.info(f"Thread für Verbindung mit {client_address} gestartet.")
        except KeyboardInterrupt:
            logging_object.info("Server wird heruntergefahren.")
        finally:
            server_socket.close()

    else:
        return

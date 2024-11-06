import socket
import threading
import time
import logging
import os


"""*****************************************************************************************************************"""


def send_data(logging_object: logging.Logger, client_socket: socket.socket, frequency: int):
    """
    Sendet Daten an Server mit gegebener Frequenz.
    :param logging_object: Logger des Clients
    :param client_socket: Verbindung zwischen Server und Client
    :param frequency: Frequenz für Nachrichtenübertragung in Hz
    :return: None
    """
    # Sendet Daten mit einem Zähler an den Server
    name = client_socket.getsockname()
    counter = 0
    period_duration = 1 / frequency
    try:
        while True:
            message = f"{name}: {str(counter)}"
            client_socket.sendall(message.encode())
            logging_object.info(f"Nachricht gesendet an Server: {message}")
            counter += 1
            time.sleep(period_duration)
    except KeyboardInterrupt:
        logging_object.info("Übertragung manuell abgebrochen.")
    except Exception as e:
        logging_object.info(f"Error: {e}")


def receive_data(logging_object: logging.Logger, client_socket: socket.socket):
    """
    Empfängt Nachrichten des Servers und damit indirekt von anderen Clients.
    :param logging_object: Logger des Clients
    :param client_socket: Verbindung zwischen Server und Client
    :return: None
    """
    # Empfängt Daten vom Server_Library
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if data:
                logging_object.info(f"Nachricht vom Server empfangen: {data}")
            else:
                logging_object.info("Verbindung zum Server beendet.")
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


def discover_server(logging_object: logging.Logger, broadcast_port: int) -> (str, int):
    """
    Empfängt Broadcast-Nachricht des Servers mit IPv4 und Port zur Kommunikation mit Server.
    :param logging_object: Logger des Clients
    :param broadcast_port: Broadcast-Port des Servers
    :return: IPv4, Port
    """
    # Wartet auf eine Broadcast-Nachricht vom Server und gibt die Server-IP und den Port zurück
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(("", broadcast_port))

    try:
        logging_object.info("Warte auf Broadcast-Nachricht vom Server...")
        data, addr = sock.recvfrom(1024)
        server_ip, port = data.decode().split(":")
        logging_object.info(f"Server gefunden: {server_ip}:{port}")
        sock.close()
        return server_ip, int(port)
    except Exception as e:
        logging_object.error(f"Error: {e}")
        return None, None


def start(logging_object: logging.Logger, frequency: int, broadcast_port: int):
    """
    Startet den Client und ruft jeweils einen Sende- und Empfangsthread auf.
    :param logging_object: Logger des Clients
    :param frequency: Sendefrequenz
    :param broadcast_port: Broadcast-Port des Servers
    :return: None
    """
    server_ip, port = discover_server(logging_object, broadcast_port)
    if not server_ip:
        logging_object.error("Fehler beim Empfangen der Serverinformationen. Starte neu...")
        start(logging_object, frequency, broadcast_port)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, port))
    logging_object.info(f"Verbunden mit dem Server: {server_ip}")

    # Erstelle einen Thread zum Senden und einen zum Empfangen
    send_thread = threading.Thread(target=send_data, args=(logging_object, client_socket, frequency))
    receive_thread = threading.Thread(target=receive_data, args=(logging_object, client_socket))

    # Starte die Threads
    send_thread.start()
    receive_thread.start()

    # Warten, bis beide Threads beendet sind
    send_thread.join()
    receive_thread.join()

    client_socket.close()

    # Neustart
    start(logging_object, frequency, broadcast_port)

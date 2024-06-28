import socket
import threading
import logging
import csv
import os
from datetime import datetime

# Initialisiere das Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Initialisiere die CSV-Datei
def initialize_csv(file_name):
    if not os.path.exists(file_name):
        with open(file_name, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Adresse", "Zeitstempel", "Daten"])


# Funktion zur Handhabung von eingehenden Verbindungen
def handle_client(client_socket, addr, file_name):
    logging.info(f"Neue Verbindung von {addr}")
    client_socket.settimeout(60)
    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8').strip()
            if not data:
                break
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            logging.info(f"Empfangene Daten von {addr} um {timestamp}: {data}")
            with open(file_name, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, addr, data])
        except socket.timeout:
            logging.warning(f"Verbindung von {addr} wurde wegen Timeout geschlossen")
            break
        except ConnectionResetError:
            logging.warning(f"Verbindung von {addr} wurde zurückgesetzt")
            break
        except Exception as e:
            logging.error(f"Fehler bei der Verbindung von {addr}: {e}")
            break
    client_socket.close()
    logging.info(f"Verbindung von {addr} geschlossen")


def main():
    csv_file = "empfangene_daten.csv"
    initialize_csv(csv_file)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 12345))
    server.listen(5)
    logging.info("Server gestartet und wartet auf Verbindungen...")

    try:
        while True:
            client_socket, addr = server.accept()
            client_handler = threading.Thread(target=handle_client, args=(client_socket, addr, csv_file))
            client_handler.start()
    except KeyboardInterrupt:
        logging.info("Server wird heruntergefahren...")
    finally:
        server.close()
        logging.info("Server wurde beendet")


if __name__ == "__main__":
    main()

import socket
import threading
import time


def discover_server(broadcast_port=50001, timeout=30):
    """Wartet auf eine Broadcast-Nachricht vom Server und gibt die Server-IP und den Port zurück"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", broadcast_port))
        sock.settimeout(timeout)

        try:
            print("Warte auf Broadcast-Nachricht vom Server...")
            data, addr = sock.recvfrom(1024)
            server_ip, port = data.decode().split(":")
            print(f"Server gefunden: {server_ip}:{port}")
            return server_ip, int(port)
        except socket.timeout:
            print("Timeout: Kein Server gefunden.")
            return None, None


def send_data(client_socket, frequency):
    """Sendet Daten mit einem Zähler alle 50 ms an den Server."""
    counter = 0
    period_duration = 1 / frequency
    try:
        while True:
            message = str(counter)
            client_socket.sendall(message.encode())
            print("Nachricht gesendet:", message)
            counter += 1
            time.sleep(period_duration)
            if counter > 100:
                break
    except KeyboardInterrupt:
        print("Übertragung manuell abgebrochen.")


def receive_data(client_socket):
    """Empfängt Daten vom Server."""
    try:
        while True:
            data = client_socket.recv(1024).decode()
            if data:
                print("Nachricht vom Server empfangen:", data)
            else:
                print("Verbindung zum Server beendet.")
                break
    except KeyboardInterrupt:
        print("Empfang manuell abgebrochen.")


def start_client(frequency):
    server_ip, port = discover_server()
    if not server_ip:
        print("Server konnte nicht gefunden werden.")
        return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_ip, port))
        print("Verbunden mit dem Server:", server_ip)

        # Erstelle einen Thread zum Senden und einen zum Empfangen
        send_thread = threading.Thread(target=send_data, args=(client_socket, frequency))
        receive_thread = threading.Thread(target=receive_data, args=(client_socket,))

        # Starte die Threads
        send_thread.start()
        receive_thread.start()

        # Warten, bis beide Threads beendet sind
        send_thread.join()
        receive_thread.join()


# Beispiel: Nachricht an den Server senden und empfangen
start_client(10)

import socket
import time


def discover_server(broadcast_port=50001, timeout=30):
    # Wartet auf eine Broadcast-Nachricht vom Server und gibt die Server-IP und den Port zurück
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", broadcast_port))
        sock.settimeout(timeout)

        try:
            print("Warte auf Broadcast-Nachricht vom Server...")
            # Daten und Absender-Adresse empfangen
            data, addr = sock.recvfrom(1024)
            server_ip, port = data.decode().split(":")
            print(f"Server gefunden: {server_ip}:{port}")
            return server_ip, int(port)
        except socket.timeout:
            print("Timeout: Kein Server gefunden.")
            return None, None


def send_message(frequency):
    # Server durch Broadcast entdecken
    server_ip, port = discover_server()
    if not server_ip:
        print("Server konnte nicht gefunden werden.")
        return

    # Verbindung herstellen und Nachricht senden
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_ip, port))

        period_duration = 1 / frequency
        counter = 0
        try:
            while True:
                message = str(counter)
                client_socket.sendall(message.encode())
                print("Nachricht gesendet:", message)
                counter += 1
                time.sleep(period_duration)  # 50 ms warten
                if counter > 100:
                    break
        except KeyboardInterrupt:
            print("Übertragung manuell abgebrochen.")
        finally:
            client_socket.close()
            print("Übertragung beendet.")


# Beispiel: Nachricht an den Server senden
send_message(100)

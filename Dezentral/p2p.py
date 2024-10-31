import socket
import threading
import time


def send_data(socket_object, broadcast_address, broadcast_port, frequency):
    # Sendet Daten mit einem Zähler alle 50 ms an den Server.
    name = socket_object.getsockname()
    counter = 0
    period_duration = 1 / frequency
    try:
        while True:
            message = f"{name}: {str(counter)}"
            socket_object.sendto(message.encode(), (broadcast_address, broadcast_port))
            print("Nachricht gesendet:", message)
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


def start_node(frequency, broadcast_address, broadcast_port):

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind((broadcast_address, broadcast_port))

    send_thread = threading.Thread(target=send_data, args=(sock, broadcast_address, broadcast_port, frequency))
    receive_thread = threading.Thread(target=receive_data, args=(sock,))

    send_thread.start()
    receive_thread.start()

    send_thread.join()
    receive_thread.join()

    sock.close()


# Start
freq = 10
bc_address = "192.168.2.255"
port = 50000
start_node(freq, bc_address, port)


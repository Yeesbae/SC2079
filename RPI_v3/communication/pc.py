import socket
import sys
from typing import Optional


class PC:
    """
    TCP server for receiving recognition results and commands from PC
    RPi acts as server, PC connects as client
    """
    def __init__(self):
        # ========== MODIFY: Change to your RPi IP address ==========
        self.host = "192.168.8.1"
        # =============================================================
        self.port = 5000
        self.connected = False
        self.server_socket = None
        self.client_socket = None

    def connect(self):
        """
        Act as TCP server, wait for PC to connect
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("Socket established successfully")

        # Binding the socket
        try:
            self.server_socket.bind((self.host, self.port))
            print("Socket binded successfully")
        except socket.error as e:
            print("Socket binding failed:", e)
            self.server_socket.close()
            sys.exit()

        # Establish connection to the PC
        print("Waiting for PC Connection...")
        try:
            self.server_socket.listen(128)
            self.client_socket, client_address = self.server_socket.accept()
            print("PC connected successfully from client address of", client_address)
        except socket.error as e:
            print("Error in getting server/client socket:", e)

        self.connected = True

    # Disconnect RPi from PC
    def disconnect(self):
        try:
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.shutdown(socket.SHUT_RDWR)
            self.server_socket.close()
            self.client_socket.close()
            self.server_socket = None
            self.client_socket = None
            self.connected = False
            print("Disconnected from PC successfully")
        except Exception as e:
            print("Failed to disconnected from PC:", e)

    # send data to PC (RPi → PC)
    def send(self, message: str) -> None:
        print("MESSAGE: ", message)
        try:
            message_bytes = message.encode("utf-8")
            self.client_socket.send(message_bytes)
            print("Sent:", message)
        except Exception as e:
            print("Failed to send message:", e)

    # receive data from PC (PC → RPi)
    def receive(self) -> Optional[str]:
        try:
            unclean_message = self.client_socket.recv(1024)
            message = unclean_message.decode("utf-8")
            # print("Message received from pc:", message)
            return message
        except OSError as e:
            print("Message failed to be received:", e)
            raise e

import socket


class PCClient:
    """
    TCP client for sending recognition results and commands to RPi
    PC acts as client, RPi acts as server
    """
    def __init__(self, host="192.168.8.1", port=5000):
        """
        Initialize TCP client
        
        Args:
            host: RPi IP address
            port: Port number
        """
        # ========== Modify as needed: set your RPi IP address ==========
        self.host = host
        # ================================================
        self.port = port
        self.client_socket = None

    def connect(self):
        """
        Connect to RPi TCP server
        """
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
            print(f"Connected to RPi at {self.host}:{self.port}")
        except OSError as e:
            print(f"Error in connecting to RPi: {e}")
            raise e

    def send(self, message: str):
        """
        Send message to RPi
        
        Args:
            message: Message string to send
        """
        try:
            self.client_socket.send(message.encode("utf-8"))
            print(f"Sent to RPi: {message}")
        except Exception as e:
            print(f"Failed to send message: {e}")
            raise e

    def receive(self) -> str:
        """
        Receive message from RPi
        
        Returns:
            Received message string
        """
        try:
            message = self.client_socket.recv(1024).decode("utf-8")
            return message
        except OSError as e:
            print(f"Error receiving message: {e}")
            raise e

    def disconnect(self):
        """Disconnect"""
        try:
            if self.client_socket:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
                self.client_socket = None
                print("Disconnected from RPi successfully")
        except Exception as e:
            print(f"Failed to disconnect: {e}")

import socket


class PCClient:
    """
    TCP客户端，用于发送识别结果和指令到RPi
    PC作为客户端，RPi作为服务器
    """
    def __init__(self, host="192.168.8.1", port=5000):
        """
        初始化TCP客户端
        
        Args:
            host: RPi的IP地址
            port: 端口号
        """
        # ========== 需要修改：改为你的RPi IP地址 ==========
        self.host = host
        # ================================================
        self.port = port
        self.client_socket = None

    def connect(self):
        """
        连接到RPi的TCP服务器
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
        发送消息到RPi
        
        Args:
            message: 要发送的消息字符串
        """
        try:
            self.client_socket.send(message.encode("utf-8"))
            print(f"Sent to RPi: {message}")
        except Exception as e:
            print(f"Failed to send message: {e}")
            raise e

    def receive(self) -> str:
        """
        接收RPi发送的消息
        
        Returns:
            接收到的消息字符串
        """
        try:
            message = self.client_socket.recv(1024).decode("utf-8")
            return message
        except OSError as e:
            print(f"Error receiving message: {e}")
            raise e

    def disconnect(self):
        """断开连接"""
        try:
            if self.client_socket:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
                self.client_socket = None
                print("Disconnected from RPi successfully")
        except Exception as e:
            print(f"Failed to disconnect from RPi: {e}")


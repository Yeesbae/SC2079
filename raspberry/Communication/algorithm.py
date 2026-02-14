"""
Algorithm Computer WiFi Communication Process
=============================================
Handles TCP/IP communication over WiFi with the algorithm computer.

The RPi acts as a WiFi Access Point, and the algorithm computer connects
to receive obstacle data and send back computed paths.

Protocol:
- JSON messages for structured data (path commands, obstacle info)
- Newline-delimited messages
- Bidirectional communication for path planning

Requirements:
- RPi configured as WiFi AP (see setup_wifi_ap in main.py)
- Algorithm computer connected to RPi's WiFi network
"""

import socket
import time
import json
import subprocess
from multiprocessing import Process, Queue
from typing import Optional, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[Algorithm/WiFi] %(message)s')
logger = logging.getLogger('Algorithm')

# WiFi Server configuration
DEFAULT_HOST = '0.0.0.0'  # Listen on all interfaces
DEFAULT_PORT = 5000
MAX_CLIENTS = 5
SOCKET_TIMEOUT = 1.0


class WiFiProcess:
    """
    WiFi TCP server for algorithm computer communication.
    
    Runs as a separate process, communicates via queues:
    - tx_queue: Messages to send to algorithm computer (from main process)
    - rx_queue: Commands/paths from algorithm computer (to main process)
    """
    
    def __init__(self, tx_queue: Queue, rx_queue: Queue, 
                 host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.tx_queue = tx_queue
        self.rx_queue = rx_queue
        self.host = host
        self.port = port
        self.server_sock: Optional[socket.socket] = None
        self.clients: List[socket.socket] = []
        self.client_buffers: dict = {}  # Buffer for each client
        self.running = False
        
    def setup_server(self) -> bool:
        """Set up TCP server."""
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(MAX_CLIENTS)
            self.server_sock.settimeout(SOCKET_TIMEOUT)
            
            logger.info(f"Server started on {self.host}:{self.port}")
            
            # Display RPi IP address for connection
            self._print_connection_info()
            
            return True
            
        except Exception as e:
            logger.error(f"Server setup error: {e}")
            return False
    
    def _print_connection_info(self):
        """Print connection info for algorithm computer."""
        try:
            # Get RPi IP addresses
            result = subprocess.check_output(['hostname', '-I']).decode().strip()
            ips = result.split()
            
            logger.info("=" * 50)
            logger.info("Algorithm computer connection info:")
            for ip in ips:
                logger.info(f"  Connect to: {ip}:{self.port}")
            logger.info("=" * 50)
            
        except Exception:
            logger.info(f"Connect to RPi on port {self.port}")
    
    def accept_connections(self):
        """Accept new client connections."""
        try:
            client_sock, addr = self.server_sock.accept()
            client_sock.settimeout(0.1)  # Non-blocking recv
            
            self.clients.append(client_sock)
            self.client_buffers[client_sock] = ""
            
            logger.info(f"Algorithm computer connected: {addr}")
            
            # Notify main process
            self.rx_queue.put({
                'type': 'CONNECT',
                'source': 'algorithm',
                'address': f"{addr[0]}:{addr[1]}"
            })
            
        except socket.timeout:
            pass
        except Exception as e:
            logger.error(f"Accept error: {e}")
    
    def broadcast(self, message: str):
        """Send message to all connected clients."""
        if not message.endswith('\n'):
            message += '\n'
        
        dead_clients = []
        
        for client in self.clients:
            try:
                client.send(message.encode('utf-8'))
            except Exception:
                dead_clients.append(client)
        
        # Remove disconnected clients
        for client in dead_clients:
            self._handle_disconnect(client)
        
        if self.clients:
            logger.info(f"TX (broadcast): {message.strip()}")
    
    def send_to_client(self, client: socket.socket, message: str) -> bool:
        """Send message to specific client."""
        if not message.endswith('\n'):
            message += '\n'
        
        try:
            client.send(message.encode('utf-8'))
            logger.info(f"TX: {message.strip()}")
            return True
        except Exception as e:
            logger.error(f"TX error: {e}")
            self._handle_disconnect(client)
            return False
    
    def receive_from_clients(self):
        """Receive data from all connected clients."""
        for client in list(self.clients):
            try:
                data = client.recv(4096).decode('utf-8', errors='ignore')
                
                if not data:
                    # Empty data means disconnect
                    self._handle_disconnect(client)
                    continue
                
                # Add to buffer
                self.client_buffers[client] += data
                
                # Process complete messages (newline-delimited)
                while '\n' in self.client_buffers[client]:
                    line, self.client_buffers[client] = self.client_buffers[client].split('\n', 1)
                    line = line.strip()
                    
                    if line:
                        self._process_message(line)
                        
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"RX error: {e}")
                self._handle_disconnect(client)
    
    def _process_message(self, message: str):
        """Process received message from algorithm computer."""
        logger.info(f"RX: {message}")
        
        try:
            # Try to parse as JSON
            data = json.loads(message)
            
            self.rx_queue.put({
                'type': 'PATH' if 'path' in data else 'DATA',
                'source': 'algorithm',
                'data': data
            })
            
        except json.JSONDecodeError:
            # Plain text command
            self.rx_queue.put({
                'type': 'COMMAND',
                'source': 'algorithm',
                'data': message
            })
    
    def _handle_disconnect(self, client: socket.socket):
        """Handle client disconnection."""
        try:
            addr = client.getpeername()
            logger.info(f"Algorithm computer disconnected: {addr}")
        except:
            logger.info("Algorithm computer disconnected")
        
        self.rx_queue.put({
            'type': 'DISCONNECT',
            'source': 'algorithm'
        })
        
        if client in self.clients:
            self.clients.remove(client)
        if client in self.client_buffers:
            del self.client_buffers[client]
        
        try:
            client.close()
        except:
            pass
    
    def run(self):
        """Main process loop."""
        logger.info("Starting WiFi communication process...")
        
        if not self.setup_server():
            logger.error("Failed to start WiFi server")
            return
        
        self.running = True
        
        while self.running:
            try:
                # Accept new connections
                self.accept_connections()
                
                # Check for messages to send
                while not self.tx_queue.empty():
                    try:
                        msg = self.tx_queue.get_nowait()
                        
                        if msg == 'SHUTDOWN':
                            self.running = False
                            break
                        
                        # Handle different message types
                        if isinstance(msg, dict):
                            self.broadcast(json.dumps(msg))
                        else:
                            self.broadcast(str(msg))
                            
                    except Exception:
                        break
                
                # Receive data from clients
                self.receive_from_clients()
                
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Process error: {e}")
                time.sleep(0.1)
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        
        if self.server_sock:
            try:
                self.server_sock.close()
            except:
                pass
        
        logger.info("WiFi process stopped")


def start_wifi_process(tx_queue: Queue, rx_queue: Queue,
                       host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Process:
    """
    Start WiFi communication as a separate process.
    
    Args:
        tx_queue: Queue for messages to send to algorithm computer
        rx_queue: Queue for commands/paths from algorithm computer
        host: Server host (default: 0.0.0.0)
        port: Server port (default: 5000)
        
    Returns:
        Process object
    """
    def _run():
        handler = WiFiProcess(tx_queue, rx_queue, host, port)
        handler.run()
    
    process = Process(target=_run, name="WiFi-Process", daemon=True)
    process.start()
    logger.info(f"Process started (PID: {process.pid})")
    return process


# Example message formats for algorithm computer
PROTOCOL_EXAMPLES = """
Algorithm Computer Protocol Examples
====================================

1. Sending obstacles to algorithm (RPi -> Algorithm):
   {"type": "obstacles", "data": [
       {"id": 1, "x": 50, "y": 100, "direction": "N", "image_id": 5},
       {"id": 2, "x": 150, "y": 50, "direction": "E", "image_id": 3}
   ]}

2. Receiving path from algorithm (Algorithm -> RPi):
   {"type": "path", "commands": [
       "SF030",  # Forward 30cm
       "RF090",  # Right turn 90 degrees
       "SF020",  # Forward 20cm
       "SNAP1",  # Take photo for obstacle 1
       ...
   ]}

3. Robot status update (RPi -> Algorithm):
   {"type": "status", "x": 20, "y": 20, "direction": "N", "state": "moving"}

4. Simple commands:
   - START: Begin path execution
   - STOP: Stop robot
   - RESET: Reset robot position
"""


# For testing standalone
if __name__ == "__main__":
    print(PROTOCOL_EXAMPLES)
    
    tx_q = Queue()
    rx_q = Queue()
    
    print("\nStarting WiFi process (standalone test)...")
    proc = start_wifi_process(tx_q, rx_q)
    
    try:
        while True:
            # Check for messages from algorithm computer
            while not rx_q.empty():
                msg = rx_q.get()
                print(f"Received: {msg}")
            
            # Read user input
            cmd = input("Enter message to broadcast (or 'q' to quit): ")
            if cmd.lower() == 'q':
                break
            if cmd:
                tx_q.put(cmd)
                
    except KeyboardInterrupt:
        pass
    
    tx_q.put('SHUTDOWN')
    proc.join(timeout=2)
    print("Done")

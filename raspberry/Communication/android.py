"""
Android Bluetooth Communication Process
=======================================
Handles Bluetooth RFCOMM communication with Android tablet (Samsung Galaxy A7 Lite).

Protocol:
- Uses Serial Port Profile (SPP) over RFCOMM
- Commands: 5-byte format from Android app
- Responses: JSON or simple ACK messages

Requirements:
- PyBluez: pip install pybluez
- Bluetooth service: sudo systemctl start bluetooth
- Run with sudo for RFCOMM access
"""

import time
from multiprocessing import Process, Queue
from typing import Optional
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='[Android/BT] %(message)s')
logger = logging.getLogger('Android')

# Bluetooth configuration
BT_CHANNEL = 1  # RFCOMM channel
BT_UUID = "00001101-0000-1000-8000-00805F9B34FB"  # Standard Serial Port UUID
BT_SERVICE_NAME = "MDP_RPi"


class BluetoothProcess:
    """
    Bluetooth RFCOMM server for Android communication.
    
    Runs as a separate process, communicates via queues:
    - tx_queue: Messages to send to Android (from main process)
    - rx_queue: Commands from Android (to main process)
    """
    
    def __init__(self, tx_queue: Queue, rx_queue: Queue, channel: int = BT_CHANNEL):
        self.tx_queue = tx_queue
        self.rx_queue = rx_queue
        self.channel = channel
        self.server_sock = None
        self.client_sock = None
        self.client_addr = None
        self.running = False
        self.bluetooth = None  # PyBluez module
        
    def setup_server(self) -> bool:
        """Set up Bluetooth RFCOMM server."""
        try:
            import bluetooth
            self.bluetooth = bluetooth
            
            # Create server socket
            self.server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.server_sock.bind(("", self.channel))
            self.server_sock.listen(1)
            self.server_sock.settimeout(1.0)  # Non-blocking accept
            
            # Advertise SPP service
            bluetooth.advertise_service(
                self.server_sock,
                BT_SERVICE_NAME,
                service_id=BT_UUID,
                service_classes=[BT_UUID, bluetooth.SERIAL_PORT_CLASS],
                profiles=[bluetooth.SERIAL_PORT_PROFILE]
            )
            
            logger.info(f"Server started on RFCOMM channel {self.channel}")
            logger.info(f"Service: {BT_SERVICE_NAME}, UUID: {BT_UUID}")
            logger.info("Waiting for Android connection...")
            return True
            
        except ImportError:
            logger.error("PyBluez not installed!")
            logger.error("Install with: sudo apt install bluetooth bluez python3-bluez && pip install pybluez")
            return False
            
        except Exception as e:
            logger.error(f"Server setup error: {e}")
            logger.error("Make sure to run with sudo and Bluetooth is enabled:")
            logger.error("  sudo systemctl start bluetooth")
            logger.error("  sudo python main.py")
            return False
    
    def accept_connection(self) -> bool:
        """Accept incoming Bluetooth connection."""
        try:
            self.client_sock, self.client_addr = self.server_sock.accept()
            self.client_sock.settimeout(0.1)  # Non-blocking recv
            logger.info(f"Android connected: {self.client_addr}")
            
            # Notify main process
            self.rx_queue.put({
                'type': 'CONNECT',
                'source': 'android',
                'address': str(self.client_addr)
            })
            return True
            
        except self.bluetooth.btcommon.BluetoothError:
            # Timeout, no connection yet
            return False
            
        except Exception as e:
            logger.error(f"Accept error: {e}")
            return False
    
    def send_message(self, message: str) -> bool:
        """Send message to Android."""
        if not self.client_sock:
            return False
        
        try:
            # Ensure message ends with newline for Android parsing
            if not message.endswith('\n'):
                message += '\n'
            self.client_sock.send(message.encode('utf-8'))
            logger.info(f"TX: {message.strip()}")
            return True
            
        except Exception as e:
            logger.error(f"TX error: {e}")
            self.handle_disconnect()
            return False
    
    def receive_data(self) -> Optional[str]:
        """Receive data from Android."""
        if not self.client_sock:
            return None
        
        try:
            data = self.client_sock.recv(1024).decode('utf-8', errors='ignore')
            if data:
                return data
            else:
                # Empty data means disconnect
                self.handle_disconnect()
                return None
                
        except self.bluetooth.btcommon.BluetoothError:
            # Timeout, no data available
            return None
            
        except Exception as e:
            logger.error(f"RX error: {e}")
            self.handle_disconnect()
            return None
    
    def handle_disconnect(self):
        """Handle client disconnection."""
        if self.client_sock:
            logger.info(f"Android disconnected: {self.client_addr}")
            self.rx_queue.put({
                'type': 'DISCONNECT',
                'source': 'android'
            })
            try:
                self.client_sock.close()
            except:
                pass
            self.client_sock = None
            self.client_addr = None
    
    def run(self):
        """Main process loop."""
        logger.info("Starting Bluetooth communication process...")
        
        if not self.setup_server():
            logger.error("Failed to start Bluetooth server")
            return
        
        self.running = True
        rx_buffer = ""
        
        while self.running:
            try:
                # Accept new connections if not connected
                if not self.client_sock:
                    self.accept_connection()
                
                # Check for messages to send to Android
                while not self.tx_queue.empty():
                    try:
                        msg = self.tx_queue.get_nowait()
                        if msg == 'SHUTDOWN':
                            self.running = False
                            break
                        
                        # Handle different message types
                        if isinstance(msg, dict):
                            self.send_message(json.dumps(msg))
                        else:
                            self.send_message(str(msg))
                    except Exception:
                        break
                
                # Receive data from Android
                if self.client_sock:
                    data = self.receive_data()
                    if data:
                        rx_buffer += data
                        
                        # Process commands (5-byte format)
                        while len(rx_buffer) >= 5:
                            cmd = rx_buffer[:5]
                            rx_buffer = rx_buffer[5:]
                            
                            # Skip newlines
                            cmd = cmd.replace('\n', '').replace('\r', '')
                            if len(cmd) < 5:
                                continue
                                
                            logger.info(f"RX: {cmd}")
                            self.rx_queue.put({
                                'type': 'COMMAND',
                                'source': 'android',
                                'data': cmd
                            })
                
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Process error: {e}")
                time.sleep(0.1)
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        if self.client_sock:
            try:
                self.client_sock.close()
            except:
                pass
        
        if self.server_sock:
            try:
                self.server_sock.close()
            except:
                pass
        
        logger.info("Bluetooth process stopped")


def start_bluetooth_process(tx_queue: Queue, rx_queue: Queue, 
                            channel: int = BT_CHANNEL) -> Process:
    """
    Start Bluetooth communication as a separate process.
    
    Args:
        tx_queue: Queue for messages to send to Android
        rx_queue: Queue for commands from Android
        channel: RFCOMM channel (default: 1)
        
    Returns:
        Process object
    """
    def _run():
        handler = BluetoothProcess(tx_queue, rx_queue, channel)
        handler.run()
    
    process = Process(target=_run, name="Bluetooth-Process", daemon=True)
    process.start()
    logger.info(f"Process started (PID: {process.pid})")
    return process


# For testing standalone
if __name__ == "__main__":
    tx_q = Queue()
    rx_q = Queue()
    
    print("Starting Bluetooth process (standalone test)...")
    print("Make sure to run with sudo!")
    proc = start_bluetooth_process(tx_q, rx_q)
    
    try:
        while True:
            # Check for messages from Android
            while not rx_q.empty():
                msg = rx_q.get()
                print(f"Received: {msg}")
            
            # Read user input
            cmd = input("Enter message to send (or 'q' to quit): ")
            if cmd.lower() == 'q':
                break
            if cmd:
                tx_q.put(cmd)
                
    except KeyboardInterrupt:
        pass
    
    tx_q.put('SHUTDOWN')
    proc.join(timeout=2)
    print("Done")

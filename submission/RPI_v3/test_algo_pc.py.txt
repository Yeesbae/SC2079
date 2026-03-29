#!/usr/bin/env python3
"""
Algorithm PC Test Client — run this on your Algorithm PC
=========================================================
TCP client that connects to RPi and allows manual command sending.

Requirements:
    python3 (no special packages needed)

Usage:
    python test_algo_pc.py                    # Connect to default RPi IP
    python test_algo_pc.py 192.168.8.1        # Connect to specific RPi IP
    python test_algo_pc.py 192.168.8.1 6000   # Custom IP and port

Before running:
    1. Start main.py on RPi in mode 4 (or mode 1 with algorithm)
    2. Make sure this PC is connected to RPi's AP network
    3. Run this script (client)
"""

import socket
import threading
import sys
import time
import json


DEFAULT_RPI_IP = "192.168.8.1"  # Default RPi AP IP address
DEFAULT_PORT = 6000
BUFFER_SIZE = 4096


class AlgoClient:
    """TCP Client for Algorithm PC"""
    
    def __init__(self, host: str = DEFAULT_RPI_IP, port: int = DEFAULT_PORT):
        """
        Initialize TCP client
        
        Args:
            host: RPi IP address to connect to
            port: Port to connect to
        """
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.running = False
    
    def connect(self) -> bool:
        """Connect to RPi TCP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"[Client] Connecting to RPi at {self.host}:{self.port}...")
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"[Client] ✓ Connected to RPi!")
            return True
        except Exception as e:
            print(f"[Client] Connection failed: {e}")
            print(f"[Client] Make sure:")
            print(f"  1. RPi is running main.py in mode 4 (or mode 1)")
            print(f"  2. This PC is connected to RPi's network")
            print(f"  3. RPi IP address is correct: {self.host}")
            print(f"  4. Port {self.port} is not blocked")
            return False
    
    def send(self, message: str) -> bool:
        """Send message to RPi"""
        if not self.connected or not self.socket:
            print("[Client] Not connected to RPi")
            return False
        
        try:
            self.socket.send(message.encode("utf-8"))
            print(f"[AlgoPC → RPi] {message}")
            return True
        except Exception as e:
            print(f"[Client] Send error: {e}")
            self.connected = False
            return False
    
    def send_json(self, data: dict) -> bool:
        """Send JSON data to RPi"""
        try:
            message = json.dumps(data)
            return self.send(message)
        except Exception as e:
            print(f"[Client] JSON error: {e}")
            return False
    
    def receive(self) -> str:
        """Receive message from RPi (blocking)"""
        if not self.connected or not self.socket:
            return None
        
        try:
            data = self.socket.recv(BUFFER_SIZE)
            if data:
                message = data.decode("utf-8")
                return message
            else:
                # Connection closed
                print("[Client] RPi disconnected")
                self.connected = False
                return None
        except Exception as e:
            print(f"[Client] Receive error: {e}")
            self.connected = False
            return None
    
    def disconnect(self):
        """Disconnect from RPi"""
        self.running = False
        self.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        print("[Client] Disconnected")


def receive_thread(client: AlgoClient):
    """Background thread to receive messages from RPi"""
    while client.running:
        if not client.connected:
            time.sleep(0.5)
            continue
        
        try:
            message = client.receive()
            if message:
                # Try to parse as JSON
                try:
                    data = json.loads(message)
                    print(f"\n[RPi → AlgoPC] (JSON) {json.dumps(data, indent=2)}")
                except json.JSONDecodeError:
                    # Plain text
                    print(f"\n[RPi → AlgoPC] {message}")
                
                print(">> ", end='', flush=True)
        except Exception as e:
            if client.running:
                print(f"\n[Error] {e}")
                print(">> ", end='', flush=True)
                time.sleep(1)


def interactive_mode(client: AlgoClient):
    """Interactive command mode"""
    print()
    print("=" * 60)
    print("ALGORITHM PC TEST CLIENT - INTERACTIVE MODE")
    print("=" * 60)
    print("Commands:")
    print("  send <text>       - Send text message to RPi")
    print("  json <json>       - Send JSON message to RPi")
    print("  path <commands>   - Send path commands (e.g., path FW100,TR090,FW050)")
    print("  status            - Show connection status")
    print("  q                 - Quit and disconnect")
    print("=" * 60)
    print()
    
    # Start receive thread
    client.running = True
    recv_thread = threading.Thread(target=receive_thread, args=(client,), daemon=True)
    recv_thread.start()
    
    try:
        while client.running:
            try:
                cmd = input(">> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            
            if not cmd:
                continue
            
            cmd_lower = cmd.lower()
            
            if cmd_lower in ('q', 'quit', 'exit'):
                break
            
            elif cmd_lower == 'status':
                status = "Connected" if client.connected else "Disconnected"
                print(f"  Status: {status}")
                if client.connected:
                    print(f"  RPi: {client.host}:{client.port}")
            
            elif cmd_lower.startswith('send '):
                message = cmd[5:].strip()
                if not client.connected:
                    print("[Error] Not connected to RPi")
                else:
                    client.send(message)
            
            elif cmd_lower.startswith('json '):
                json_str = cmd[5:].strip()
                try:
                    data = json.loads(json_str)
                    if not client.connected:
                        print("[Error] Not connected to RPi")
                    else:
                        client.send_json(data)
                except json.JSONDecodeError as e:
                    print(f"[Error] Invalid JSON: {e}")
            
            elif cmd_lower.startswith('path '):
                # Parse path commands and send as JSON
                commands_str = cmd[5:].strip()
                commands = [c.strip() for c in commands_str.split(',')]
                path_data = {
                    "type": "path",
                    "commands": commands
                }
                if not client.connected:
                    print("[Error] Not connected to RPi")
                else:
                    client.send_json(path_data)
            
            else:
                # Treat as message to send
                if not client.connected:
                    print("[Error] Not connected to RPi")
                else:
                    client.send(cmd)
    
    except KeyboardInterrupt:
        print("\n\nInterrupted")
    finally:
        client.running = False


def main():
    print()
    print("=" * 60)
    print("Algorithm PC Test Client")
    print("=" * 60)
    print()
    
    # Get RPi IP and port from command line
    rpi_ip = DEFAULT_RPI_IP
    port = DEFAULT_PORT
    
    if len(sys.argv) > 1:
        rpi_ip = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(f"Invalid port number. Using default: {DEFAULT_PORT}")
            port = DEFAULT_PORT
    
    # Connect to RPi
    client = AlgoClient(rpi_ip, port)
    if not client.connect():
        sys.exit(1)
    
    # Enter interactive mode
    try:
        interactive_mode(client)
    finally:
        client.disconnect()
        print("\n[Done] Client shut down")


if __name__ == "__main__":
    main()

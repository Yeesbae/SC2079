#!/usr/bin/env python3
"""
Bluetooth PC Tester — run this on your PC (NOT the RPi)
=========================================================
Tests 2-way Bluetooth (SPP/RFCOMM) communication with the RPi.

Requirements (install on your PC):
    Windows (recommended):
        pip install pyserial          # COM port approach (most reliable on Windows)

    Linux:
        sudo apt install bluetooth libbluetooth-dev python3-dev
        pip install PyBluez pyserial

Usage:
    python test_bt_pc.py              # auto-detect (COM port on Windows, socket on Linux)
    python test_bt_pc.py com          # Windows: list COM ports and pick one
    python test_bt_pc.py COM5         # Windows: connect directly to COM5
    python test_bt_pc.py socket       # force raw socket mode (Linux default)
    python test_bt_pc.py scan         # scan for RPi then connect via socket

Before running:
    1. Start main.py on RPi and select mode 2 (Bluetooth Only Test)
    2. Pair this PC with the RPi ('chicken') in OS Bluetooth settings
    3. Windows: check Device Manager > Ports for the outgoing COM port number
"""

import sys
import os
import socket
import threading
import time

IS_WINDOWS = sys.platform == "win32"

# ─────────────────────────────────────────────────────────
# CONFIG — update RPI_MAC if needed
# ─────────────────────────────────────────────────────────
RPI_NAME        = "chicken"
RPI_MAC         = "E4:5F:01:A3:B1:4D"
SPP_UUID        = "00001101-0000-1000-8000-00805F9B34FB"
RECV_BUFFER     = 1024
FALLBACK_CHANNELS = [1, 2, 3, 4, 5]


# ─────────────────────────────────────────────────────────
# Windows COM Port helpers
# ─────────────────────────────────────────────────────────

def list_com_ports():
    try:
        import serial.tools.list_ports
        return list(serial.tools.list_ports.comports())
    except ImportError:
        return []


def wait_for_com_ports(max_wait_seconds=10):
    """Wait for COM ports to appear (useful after Bluetooth reconnection)"""
    print("\n[COM] Waiting for COM ports to appear...")
    for i in range(max_wait_seconds):
        ports = list_com_ports()
        if ports:
            print(f"[COM] Found {len(ports)} port(s)")
            return ports
        print(f"  Waiting... ({i+1}/{max_wait_seconds})", end='\r')
        time.sleep(1)
    print("\n[COM] Timeout waiting for COM ports")
    return []


def find_bluetooth_com_port():
    ports = list_com_ports()
    bt_ports = [p for p in ports if
                "bluetooth" in p.description.lower() or
                "standard serial" in p.description.lower() or
                RPI_NAME.lower() in p.description.lower()]
    return bt_ports, ports


def pick_com_port(retry_if_empty=True) -> str:
    bt_ports, all_ports = find_bluetooth_com_port()

    print("\n[COM] Available ports:")
    if not all_ports:
        if retry_if_empty:
            print("  No COM ports found.")
            print("  This can happen after Bluetooth disconnect/reconnect.")
            choice = input("  Wait for ports to appear? (y/n): ").strip().lower()
            if choice == 'y':
                all_ports = wait_for_com_ports()
                bt_ports = [p for p in all_ports if
                           "bluetooth" in p.description.lower() or
                           "standard serial" in p.description.lower() or
                           RPI_NAME.lower() in p.description.lower()]
        
        if not all_ports:
            print("\n  Troubleshooting:")
            print("  1. Reconnect Bluetooth in Windows settings")
            print("  2. Wait 5-10 seconds for COM port to appear")
            print("  3. Check Device Manager > Ports (COM & LPT)")
            print("  4. Try again or install pyserial: pip install pyserial")
            return ""

    for i, p in enumerate(all_ports):
        flag = " ← Bluetooth" if p in bt_ports else ""
        print(f"  {i+1}. {p.device:8s}  {p.description}{flag}")

    if bt_ports:
        print(f"\n  Auto-detected Bluetooth port(s): {[p.device for p in bt_ports]}")
        print("  Tip: use the OUTGOING port (not incoming)")

    choice = input("\nEnter COM port name or number (e.g. COM5 or 2): ").strip()
    if not choice:
        return ""
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(all_ports):
            return all_ports[idx].device
    return choice.upper() if IS_WINDOWS else choice


# ─────────────────────────────────────────────────────────
# COM Port Client (Windows recommended)
# ─────────────────────────────────────────────────────────

class COMClient:
    def __init__(self, port: str, baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        self._running = False

    def connect(self) -> bool:
        try:
            import serial
            print(f"[COM] Connecting to {self.port} at {self.baudrate} baud...")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.connected = True
            print(f"[COM] ✓ Connected on {self.port}!")
            return True
        except ImportError:
            print("[COM] ✗ pyserial not installed.  Run: pip install pyserial")
        except Exception as e:
            print(f"[COM] ✗ Failed: {e}")
        return False

    def send(self, message: str) -> bool:
        if not self.connected or not self.ser:
            return False
        try:
            self.ser.write((message + "\n").encode("utf-8"))
            self.ser.flush()
            return True
        except Exception as e:
            print(f"[COM] Send error: {e}")
            self.connected = False
            return False

    def disconnect(self):
        self._running = False
        self.connected = False
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
            self.ser = None

    def _recv_loop(self):
        while self._running and self.connected:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode("utf-8", errors="replace").strip()
                    if line:
                        print(f"\n  [RPi → PC]  {line}")
                        print(">> ", end="", flush=True)
                else:
                    time.sleep(0.05)
            except OSError as e:
                if self._running:
                    if "device has been removed" in str(e).lower() or e.errno == 22:
                        print(f"\n[COM] Bluetooth device disconnected")
                        print("[COM] To reconnect:")
                        print("  1. Reconnect Bluetooth in Windows settings")
                        print("  2. Wait 5-10 seconds")
                        print("  3. Rerun the script")
                    else:
                        print(f"\n[COM] Receive error: {e}")
                self.connected = False
                break
            except Exception as e:
                if self._running:
                    print(f"\n[COM] Receive error: {e}")
                self.connected = False
                break


# ─────────────────────────────────────────────────────────
# Raw Socket Client (Linux / fallback)
# ─────────────────────────────────────────────────────────

class BTSocketClient:
    def __init__(self, mac: str, channel: int):
        self.mac = mac
        self.channel = channel
        self.sock = None
        self.connected = False
        self._running = False

    def _try_channel(self, channel: int) -> bool:
        try:
            print(f"[BT] Trying channel {channel}...", end=" ", flush=True)
            self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            self.sock.settimeout(6)
            self.sock.connect((self.mac, channel))
            self.sock.settimeout(None)
            self.channel = channel
            return True
        except (socket.timeout, TimeoutError):
            print("timeout")
        except ConnectionRefusedError:
            print("refused")
        except OSError as e:
            code = getattr(e, 'winerror', e.errno)
            if code in (10064, 10061):
                print("host unreachable — ensure RPi main.py is running")
            else:
                print(f"OS error: {e}")
        except Exception as e:
            print(f"failed ({e})")
        try:
            self.sock.close()
        except:
            pass
        self.sock = None
        return False

    def connect(self) -> bool:
        channels = [self.channel] if self.channel != 0 else FALLBACK_CHANNELS
        print(f"[BT] Connecting to {self.mac}...")
        for ch in channels:
            if self._try_channel(ch):
                self.connected = True
                print(f"[BT] ✓ Connected on channel {ch}!")
                return True
        print("[BT] ✗ Could not connect on any channel.")
        return False

    def send(self, message: str) -> bool:
        if not self.connected or not self.sock:
            return False
        try:
            self.sock.sendall((message + "\n").encode("utf-8"))
            return True
        except Exception as e:
            print(f"[BT] Send error: {e}")
            self.connected = False
            return False

    def disconnect(self):
        self._running = False
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def _recv_loop(self):
        buf = ""
        while self._running and self.connected:
            try:
                self.sock.settimeout(0.5)
                chunk = self.sock.recv(RECV_BUFFER)
                self.sock.settimeout(None)
                if not chunk:
                    print("\n[BT] Connection closed by RPi.")
                    self.connected = False
                    break
                buf += chunk.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        print(f"\n  [RPi → PC]  {line}")
                        print(">> ", end="", flush=True)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"\n[BT] Receive error: {e}")
                self.connected = False
                break


def find_socket_channel(mac: str) -> int:
    try:
        import bluetooth
        print(f"[SDP] Looking up SPP service on {mac}...")
        services = bluetooth.find_service(uuid=SPP_UUID, address=mac)
        if services:
            for s in services:
                print(f"[SDP] Found: '{s.get('name')}' on channel {s.get('port')}")
            return services[0]["port"]
        print("[SDP] No SPP service found. Will try channels 1-5.")
    except ImportError:
        print("[SDP] PyBluez not installed — skipping SDP. Will try channels 1-5.")
    except Exception as e:
        print(f"[SDP] Lookup failed ({e}). Will try channels 1-5.")
    return 0


def scan_for_rpi() -> str:
    try:
        import bluetooth
        print(f"[Scan] Scanning for '{RPI_NAME}'... (takes ~10 seconds)")
        devices = bluetooth.discover_devices(duration=8, lookup_names=True, flush_cache=True)
        for addr, name in devices:
            print(f"  • {name:30s} [{addr}]")
            if name == RPI_NAME:
                print(f"[Scan] ✓ Found: {name} @ {addr}")
                return addr
        print(f"[Scan] '{RPI_NAME}' not found. Using default: {RPI_MAC}")
    except Exception as e:
        print(f"[Scan] Error: {e}")
    return RPI_MAC


# ─────────────────────────────────────────────────────────
# Interactive Shell (shared by both client types)
# ─────────────────────────────────────────────────────────

def run_shell(client):
    label = (client.port if isinstance(client, COMClient)
             else f"{client.mac} ch{client.channel}")
    print()
    print("━" * 55)
    print(f"  ✓ Connected to RPi '{RPI_NAME}'  [{label}]")
    print("━" * 55)
    print("  Type any message and press Enter to send.")
    print("  Commands: ping / hello / status / q")
    print("━" * 55)
    print()

    client._running = True
    t = threading.Thread(target=client._recv_loop, daemon=True)
    t.start()

    try:
        while client.connected:
            try:
                raw = input(">> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not raw:
                continue
            cmd = raw.lower()

            if cmd in ("q", "quit", "exit"):
                break
            elif cmd == "status":
                print(f"  State : {'Connected' if client.connected else 'Disconnected'}")
                print(f"  Target: {label}")
            elif cmd in ("ping", "hello"):
                msg = cmd.upper()
                if client.send(msg):
                    print(f"  [PC → RPi]  {msg}")
            else:
                if client.send(raw):
                    print(f"  [PC → RPi]  {raw}")
                else:
                    print("  [ERROR] Send failed — connection lost.")
                    break
    finally:
        client._running = False
        client.disconnect()
        print("\n[Done] Disconnected.")


# ─────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────

def main():
    print()
    print("━" * 55)
    print("  RPi Bluetooth Tester (PC side)")
    print("━" * 55)

    arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""

    # ── Windows COM port mode (recommended on Windows) ────
    if IS_WINDOWS and arg not in ("socket", "scan") and ":" not in arg:
        if arg.startswith("com") and len(arg) > 3:
            port = arg.upper()
        else:
            # No port given — show list and let user pick
            print()
            port = pick_com_port()

        if not port:
            print("[Error] No COM port selected.")
            sys.exit(1)

        client = COMClient(port)
        if not client.connect():
            print()
            print("━" * 55)
            print("  Windows Troubleshooting:")
            print("  1. Start main.py on RPi → select mode 2 or 3")
            print(f"  2. Pair PC with '{RPI_NAME}' in Windows Bluetooth settings")
            print("  3. Wait 5-10 seconds for COM port to appear")
            print("  4. Open Device Manager → Ports (COM & LPT)")
            print("     Find 'Standard Serial over Bluetooth link (COMx)' — Outgoing")
            print("     Use that number: python test_bt_pc.py COM5")
            print("  5. pip install pyserial")
            print()
            print("  After Bluetooth disconnection:")
            print("  - Reconnect Bluetooth in Windows settings")
            print("  - Wait 5-10 seconds for COM port to recreate")
            print("  - Rerun this script")
            print("━" * 55)
            sys.exit(1)

    # ── Linux / forced socket mode ─────────────────────────
    else:
        if arg == "scan":
            mac = scan_for_rpi()
        elif ":" in arg:
            mac = sys.argv[1]
        else:
            mac = RPI_MAC
            print(f"[Config] Using default MAC: {mac}")

        channel = find_socket_channel(mac)
        print()
        client = BTSocketClient(mac, channel)
        if not client.connect():
            print()
            print("━" * 55)
            print("  Troubleshooting:")
            print("  1. Start main.py on RPi → select mode 2 or 3")
            print(f"  2. Pair PC with '{RPI_NAME}' in OS Bluetooth settings")
            print("  3. On RPi: bluetoothctl discoverable on")
            print(f"  4. Verify MAC: {mac}")
            print("  5. After disconnection, wait a few seconds before reconnecting")
            print("━" * 55)
            sys.exit(1)

    run_shell(client)


if __name__ == "__main__":
    main()

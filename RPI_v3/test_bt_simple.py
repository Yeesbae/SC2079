#!/usr/bin/env python3
"""
Simple Bluetooth Connection Test

This script helps diagnose and fix Bluetooth connection issues.
Run this before running main.py to ensure ports are free.

Usage:
    sudo python3 test_bt_simple.py
"""
import socket
import subprocess
import sys
import time


def run_cmd(cmd, check=False):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1


def main():
    print("=" * 60)
    print("Bluetooth Connection Diagnostic & Fix Tool")
    print("=" * 60)
    
    # Check if running as root (needed for some commands)
    if subprocess.run(['id', '-u'], capture_output=True, text=True).stdout.strip() != '0':
        print("\n[WARNING] Not running as root. Some fixes may not work.")
        print("Consider running: sudo python3 test_bt_simple.py\n")
    
    # 1. Check Bluetooth status
    print("\n[1] Checking Bluetooth service status...")
    out, _ = run_cmd("systemctl is-active bluetooth")
    print(f"    Bluetooth service: {out}")
    
    # 2. Check for existing RFCOMM connections
    print("\n[2] Checking existing RFCOMM connections...")
    out, _ = run_cmd("rfcomm -a")
    if out:
        print(f"    Active RFCOMM:\n    {out}")
    else:
        print("    No active RFCOMM connections")
    
    # 3. Check what's using Bluetooth
    print("\n[3] Checking processes using Bluetooth...")
    out, _ = run_cmd("lsof /dev/rfcomm* 2>/dev/null | head -10")
    if out:
        print(f"    Processes using RFCOMM:\n    {out}")
    else:
        print("    No processes found using RFCOMM devices")
    
    # 4. Ask user if they want to fix
    print("\n" + "=" * 60)
    fix = input("Do you want to release all RFCOMM ports? (y/n): ").strip().lower()
    
    if fix == 'y':
        print("\n[4] Releasing RFCOMM ports...")
        
        # Release all rfcomm
        out, code = run_cmd("sudo rfcomm release all 2>&1")
        print(f"    rfcomm release all: {out if out else 'OK'}")
        
        # Kill any rfcomm processes
        out, code = run_cmd("sudo killall rfcomm 2>&1")
        print(f"    killall rfcomm: {out if out else 'OK (or no process found)'}")
        
        # Restart bluetooth service
        restart = input("\nRestart Bluetooth service? (y/n): ").strip().lower()
        if restart == 'y':
            print("    Restarting bluetooth service...")
            run_cmd("sudo systemctl restart bluetooth")
            time.sleep(2)
            print("    Done!")
    
    # 5. Test connection
    print("\n" + "=" * 60)
    test = input("Do you want to test Bluetooth connection now? (y/n): ").strip().lower()
    
    if test == 'y':
        try:
            import bluetooth
            print("\n[5] Testing Bluetooth connection...")
            
            # Try to create and bind socket
            for port in [1, 2, 3, 4, 5]:
                print(f"    Trying RFCOMM channel {port}...", end=" ")
                try:
                    sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                    sock.bind(("", port))
                    sock.listen(1)
                    print("✓ Available!")
                    sock.close()
                    
                    # Ask if user wants to wait for connection on this port
                    wait = input(f"\n    Wait for connection on channel {port}? (y/n): ").strip().lower()
                    if wait == 'y':
                        print(f"\n    Waiting for connection on RFCOMM channel {port}...")
                        print("    (Connect from your PC/Android now)")
                        print("    Press Ctrl+C to cancel\n")
                        
                        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                        sock.bind(("", port))
                        sock.listen(1)
                        sock.settimeout(60)
                        
                        try:
                            client, addr = sock.accept()
                            print(f"    ✓ Connected from {addr}!")
                            
                            # Simple echo test
                            print("\n    Starting echo test (type 'quit' to exit)...")
                            client.settimeout(1)
                            
                            while True:
                                # Check for incoming data  
                                try:
                                    data = client.recv(1024)
                                    if data:
                                        msg = data.decode('utf-8').strip()
                                        print(f"    [RECV] {msg}")
                                        client.send(f"ECHO: {msg}\n".encode())
                                except:
                                    pass
                                
                                # Send user input
                                try:
                                    import select
                                    if select.select([sys.stdin], [], [], 0.1)[0]:
                                        user_input = input()
                                        if user_input.lower() == 'quit':
                                            break
                                        client.send(f"{user_input}\n".encode())
                                        print(f"    [SENT] {user_input}")
                                except:
                                    pass
                            
                            client.close()
                        except (socket.timeout, bluetooth.btcommon.BluetoothError) as e:
                            if "timed out" in str(e):
                                print("    Timeout - no connection received within 60 seconds")
                            else:
                                print(f"    Error: {e}")
                        except Exception as e:
                            print(f"    Error: {e}")
                        finally:
                            sock.close()
                    break
                    
                except OSError as e:
                    print(f"✗ In use ({e})")
                    
        except ImportError:
            print("\n[ERROR] PyBluez not installed!")
            print("Install with: sudo apt-get install python3-bluez bluetooth bluez")
    
    print("\n" + "=" * 60)
    print("Done! You can now try running: python3 main.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

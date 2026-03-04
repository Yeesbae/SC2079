#!/usr/bin/env python3
"""
Bluetooth 2-Way Communication Test Script

This script tests bidirectional Bluetooth communication between RPi and Android.
Both RPi and Android can send and receive messages.

Usage:
    python test_bluetooth.py

Commands during runtime:
    - Type any message and press Enter to send to Android
    - Type 'q' to quit
    - Messages from Android will be displayed automatically
"""
import threading
import time
import sys
from communication.bluetooth import BluetoothHandler


class BluetoothTester:
    def __init__(self):
        self.bt = BluetoothHandler()
        self.running = False
        self.receive_thread = None
        
    def start(self):
        """Start the Bluetooth test"""
        print("=" * 60)
        print("Bluetooth 2-Way Communication Test")
        print("=" * 60)
        
        # Connect to Bluetooth
        print("\n[1] Waiting for Android to connect...")
        if not self.bt.connect():
            print("Failed to connect. Exiting.")
            return
        
        print("\n[2] Connection established!")
        print("=" * 60)
        print("Commands:")
        print("  - Type any message and press Enter to send to Android")
        print("  - Type 'q' to quit")
        print("  - Messages from Android will be displayed automatically")
        print("=" * 60)
        
        self.running = True
        
        # Start receive thread
        self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.receive_thread.start()
        
        # Main loop - handle sending
        self.send_loop()
        
    def receive_loop(self):
        """Thread to continuously receive messages from Android"""
        print("\n[Receiver] Started listening for messages from Android...")
        
        while self.running:
            try:
                # Non-blocking receive with short timeout
                message = self.bt.receive_nonblocking(timeout=0.1)
                if message:
                    print(f"\n[RECEIVED from Android] >>> {message}")
                    print("Enter message to send (or 'q' to quit): ", end='', flush=True)
                    
                    # Echo back to confirm receipt
                    self.bt.send(f"RPi received: {message}")
                    
            except Exception as e:
                if self.running:
                    print(f"\n[Receiver] Error: {e}")
                break
                
        print("[Receiver] Stopped")
        
    def send_loop(self):
        """Main loop to handle user input and send messages"""
        try:
            while self.running:
                # Get user input
                message = input("\nEnter message to send (or 'q' to quit): ").strip()
                
                if message.lower() == 'q':
                    print("\nQuitting...")
                    break
                    
                if message:
                    # Send message to Android
                    if self.bt.send(message):
                        print(f"[SENT to Android] <<< {message}")
                    else:
                        print("[ERROR] Failed to send message")
                        
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        finally:
            self.stop()
            
    def stop(self):
        """Stop the test and cleanup"""
        self.running = False
        time.sleep(0.2)  # Allow receive thread to exit
        self.bt.disconnect()
        print("\n[Test] Bluetooth test ended")


class BluetoothAutoTester:
    """
    Automated test that sends periodic messages and echoes received messages.
    Useful for testing without manual input.
    """
    def __init__(self, send_interval: float = 5.0):
        self.bt = BluetoothHandler()
        self.running = False
        self.send_interval = send_interval
        self.message_count = 0
        
    def start(self):
        """Start automated test"""
        print("=" * 60)
        print("Bluetooth Automated 2-Way Test")
        print(f"Will send test messages every {self.send_interval} seconds")
        print("=" * 60)
        
        if not self.bt.connect():
            print("Failed to connect. Exiting.")
            return
            
        print("\nConnection established! Starting automated test...")
        print("Press Ctrl+C to stop\n")
        
        self.running = True
        
        # Start receive thread
        receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
        receive_thread.start()
        
        # Start send thread
        send_thread = threading.Thread(target=self.send_loop, daemon=True)
        send_thread.start()
        
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\nStopping automated test...")
        finally:
            self.stop()
            
    def receive_loop(self):
        """Receive and echo messages"""
        while self.running:
            try:
                message = self.bt.receive_nonblocking(timeout=0.1)
                if message:
                    print(f"[RECEIVED] >>> {message}")
                    # Echo back
                    self.bt.send(f"ECHO: {message}")
            except:
                break
                
    def send_loop(self):
        """Send periodic test messages"""
        while self.running:
            self.message_count += 1
            test_msg = f"TEST_MSG_{self.message_count:04d}"
            
            if self.bt.send(test_msg):
                print(f"[SENT] <<< {test_msg}")
            
            time.sleep(self.send_interval)
            
    def stop(self):
        self.running = False
        time.sleep(0.2)
        self.bt.disconnect()
        print(f"\n[Test] Completed. Sent {self.message_count} messages.")


def main():
    print("\nBluetooth Communication Test")
    print("=" * 40)
    print("Select test mode:")
    print("  1. Interactive (manual send/receive)")
    print("  2. Automated (periodic send, auto-echo)")
    print("  q. Quit")
    
    while True:
        choice = input("\nEnter choice (1/2/q): ").strip().lower()
        
        if choice == '1':
            tester = BluetoothTester()
            tester.start()
            break
        elif choice == '2':
            interval = input("Send interval in seconds (default 5): ").strip()
            try:
                interval = float(interval) if interval else 5.0
            except ValueError:
                interval = 5.0
            tester = BluetoothAutoTester(send_interval=interval)
            tester.start()
            break
        elif choice == 'q':
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or q.")


if __name__ == "__main__":
    main()

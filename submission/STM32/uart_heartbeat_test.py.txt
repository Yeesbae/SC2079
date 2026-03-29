"""
UART Heartbeat Test
====================
Listens for heartbeat messages from STM32 to verify UART3 TX is working.
Also allows sending test commands.
"""

import serial
import serial.tools.list_ports
import sys
import time


def list_ports():
    """List available serial ports."""
    print("\nAvailable Serial Ports:")
    print("-" * 40)
    ports = serial.tools.list_ports.comports()
    for i, p in enumerate(ports):
        print(f"  [{i}] {p.device} - {p.description}")
    print("-" * 40)
    return ports


def main():
    print("=" * 50)
    print("STM32 UART Heartbeat Test")
    print("=" * 50)

    # List and select port
    ports = list_ports()

    if not ports:
        print("No serial ports found!")
        sys.exit(1)

    # Auto-select if only one CH9102 port
    ch9102_ports = [p for p in ports if 'CH9102' in p.description]

    if len(ch9102_ports) == 1:
        port = ch9102_ports[0].device
        print(f"\nAuto-selected: {port}")
    else:
        choice = input("\nEnter port (e.g., COM5): ").strip()
        port = choice.upper() if not choice.startswith('/') else choice

    # Connect
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1
        )
        print(f"Connected to {port} at 115200 baud\n")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Listening for heartbeats (HB) from STM32...")
    print("Type a 5-char command (e.g., SF050) and press Enter to send")
    print("Type 'quit' to exit\n")
    print("-" * 50)

    hb_count = 0
    rx_count = 0

    try:
        while True:
            # Check for incoming data
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                rx_count += len(data)

                # Decode and display
                try:
                    text = data.decode('utf-8', errors='replace')

                    # Count heartbeats
                    hb_count += text.count('HB')

                    # Print received data
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] RX ({len(data)} bytes): {repr(text)}  | Total HB: {hb_count}")

                except Exception as e:
                    print(f"[RX] Raw: {data.hex()}")

            # Check for user input (non-blocking on Windows requires different approach)
            # Simple approach: use timeout
            import msvcrt
            if msvcrt.kbhit():
                # Read user input
                user_input = input()

                if user_input.lower() == 'quit':
                    break
                elif len(user_input) == 5:
                    # Send 5-byte command
                    ser.write(user_input.encode())
                    print(f"[TX] Sent: {user_input}")
                elif user_input:
                    print(f"Command must be 5 chars (got {len(user_input)}). Example: SF050")

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        print(f"\nSummary: Received {hb_count} heartbeats, {rx_count} total bytes")
        ser.close()
        print("Port closed.")


if __name__ == "__main__":
    main()

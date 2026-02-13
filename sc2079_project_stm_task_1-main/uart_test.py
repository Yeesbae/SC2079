"""
STM32 UART Communication Test Script
=====================================
Sends movement commands to STM32 and waits for acknowledgment.

Command Format (5 bytes): [CMD][DIR][D1][D2][D3]
- CMD: S=Straight, R=Right, L=Left, U=Ultrasonic, G=Gyro Reset
- DIR: F=Forward, B=Backward
- D1D2D3: 3-digit magnitude (e.g., 090 = 90 units)

Examples:
- SF050 = Move straight forward 50 cm
- SB030 = Move straight backward 30 cm
- RF090 = Turn right 90 degrees
- RB090 = Turn right backward 90 degrees
- LF045 = Turn left 45 degrees
- LB045 = Turn left backward 45 degrees
- UF000 = Ultrasonic command forward
- GF000 = Gyro reset

Acknowledgment: STM32 sends 'A' when command is completed
"""

import serial
import serial.tools.list_ports
import time
import sys


def list_serial_ports():
    """List all available serial ports."""
    ports = serial.tools.list_ports.comports()
    print("\nAvailable Serial Ports:")
    print("-" * 40)
    for i, port in enumerate(ports):
        print(f"  [{i}] {port.device} - {port.description}")
    print("-" * 40)
    return ports


def connect_to_stm32(port, baudrate=115200):
    """Establish serial connection to STM32."""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=10  # 10 second timeout for acknowledgment
        )
        print(f"\nConnected to {port} at {baudrate} baud")
        return ser
    except serial.SerialException as e:
        print(f"Error: Could not open {port}: {e}")
        return None


def send_command(ser, cmd):
    """Send a 5-byte command and wait for acknowledgment."""
    if len(cmd) != 5:
        print(f"Error: Command must be exactly 5 characters, got {len(cmd)}")
        return False

    # Clear any pending data
    ser.reset_input_buffer()

    # Send command
    print(f"\nSending: '{cmd}' (hex: {cmd.encode().hex()})")
    ser.write(cmd.encode())
    ser.flush()

    # Wait for acknowledgment
    print("Waiting for acknowledgment...")
    start_time = time.time()

    while True:
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"Received: '{response.decode(errors='ignore')}' (hex: {response.hex()})")

            if b'A' in response:
                elapsed = time.time() - start_time
                print(f"Command completed! (took {elapsed:.2f} seconds)")
                return True

        # Timeout check
        if time.time() - start_time > 10:
            print("Timeout: No acknowledgment received within 10 seconds")
            return False

        time.sleep(0.01)


def build_command(cmd_type, direction, magnitude):
    """Build a 5-byte command string."""
    cmd_type = cmd_type.upper()
    direction = direction.upper()

    if cmd_type not in ['S', 'R', 'L', 'U', 'G']:
        raise ValueError("Command type must be S, R, L, U, or G")

    if direction not in ['F', 'B']:
        raise ValueError("Direction must be F or B")

    if not 0 <= magnitude <= 999:
        raise ValueError("Magnitude must be 0-999")

    return f"{cmd_type}{direction}{magnitude:03d}"


def interactive_mode(ser):
    """Interactive command mode."""
    print("\n" + "=" * 50)
    print("INTERACTIVE MODE")
    print("=" * 50)
    print("Commands:")
    print("  1. straight <distance> [f/b]  - Move straight (cm)")
    print("  2. right <angle> [f/b]        - Turn right (degrees)")
    print("  3. left <angle> [f/b]         - Turn left (degrees)")
    print("  4. raw <5-char-cmd>           - Send raw 5-byte command")
    print("  5. test                       - Run test sequence")
    print("  6. quit                       - Exit program")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n> ").strip().lower()

            if not user_input:
                continue

            parts = user_input.split()
            command = parts[0]

            if command == 'quit' or command == 'q':
                print("Exiting...")
                break

            elif command == 'straight' or command == 's':
                dist = int(parts[1]) if len(parts) > 1 else 50
                direction = parts[2].upper() if len(parts) > 2 else 'F'
                cmd = build_command('S', direction, abs(dist))
                send_command(ser, cmd)

            elif command == 'right' or command == 'r':
                angle = int(parts[1]) if len(parts) > 1 else 90
                direction = parts[2].upper() if len(parts) > 2 else 'F'
                cmd = build_command('R', direction, abs(angle))
                send_command(ser, cmd)

            elif command == 'left' or command == 'l':
                angle = int(parts[1]) if len(parts) > 1 else 90
                direction = parts[2].upper() if len(parts) > 2 else 'F'
                cmd = build_command('L', direction, abs(angle))
                send_command(ser, cmd)

            elif command == 'raw':
                if len(parts) > 1 and len(parts[1]) == 5:
                    send_command(ser, parts[1].upper())
                else:
                    print("Usage: raw <5-char-command>  e.g., raw SF050")

            elif command == 'test':
                print("\n--- Running Test Sequence ---")

                print("\nTest 1: Move forward 20 cm")
                send_command(ser, "SF020")
                time.sleep(1)

                print("\nTest 2: Turn right 45 degrees")
                send_command(ser, "RF045")
                time.sleep(1)

                print("\nTest 3: Turn left 45 degrees")
                send_command(ser, "LF045")
                time.sleep(1)

                print("\nTest 4: Move backward 20 cm")
                send_command(ser, "SB020")

                print("\n--- Test Sequence Complete ---")

            else:
                print(f"Unknown command: {command}")
                print("Type 'quit' to exit or see commands above")

        except ValueError as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    print("=" * 50)
    print("STM32 UART Communication Test")
    print("=" * 50)

    # List available ports
    ports = list_serial_ports()

    if not ports:
        print("No serial ports found!")
        sys.exit(1)

    # Select port
    if len(ports) == 1:
        selected_port = ports[0].device
        print(f"\nAuto-selecting: {selected_port}")
    else:
        try:
            choice = input("\nSelect port number (or enter COM port directly): ").strip()
            if choice.isdigit():
                selected_port = ports[int(choice)].device
            else:
                selected_port = choice.upper() if not choice.startswith('/') else choice
        except (ValueError, IndexError):
            print("Invalid selection")
            sys.exit(1)

    # Connect
    ser = connect_to_stm32(selected_port)
    if not ser:
        sys.exit(1)

    # Wait for STM32 boot message
    print("\nWaiting for STM32 boot message...")
    time.sleep(2)

    if ser.in_waiting > 0:
        boot_msg = ser.read(ser.in_waiting)
        print(f"STM32 says: {boot_msg.decode(errors='ignore')}")

    # Enter interactive mode
    try:
        interactive_mode(ser)
    finally:
        ser.close()
        print("Serial port closed.")


if __name__ == "__main__":
    main()

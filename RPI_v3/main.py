"""
RPI_v3 Main Entry Point

This version includes a Bluetooth communication test mode for verifying
2-way communication between RPi and Android before running full task.

Modes:
    1. Full Task Mode (with BT + PC + Algorithm)
    2. Bluetooth Only Test Mode (for testing BT communication)
"""
import multiprocessing as mp
from multiprocessing import Process, Queue, Event
import time
import sys
import threading

from config.config import get_config, Config


# =============================================================================
# Process 1: Bluetooth (Android Communication)
# =============================================================================
def bluetooth_process(
    to_algo_queue: Queue,      # Send obstacle coords to Algorithm
    from_task_queue: Queue,    # Receive image rec results from Task
    to_task_queue: Queue,      # Send commands to Task (future use)
    from_algo_queue: Queue,    # Receive commands from Algorithm (to forward to Android)
    stop_event: Event,
    config: Config
):
    """
    Bluetooth process - handles Android communication with auto-reconnect
    """
    # Import here for multiprocessing spawn compatibility
    from communication.bluetooth import BluetoothHandler
    import re
    
    print("[BT Process] Starting...")
    
    bt = BluetoothHandler()
    
    # STM32 command pattern: SF050, STOP, etc.
    stm32_cmd_pattern = re.compile(r'^([A-Z]{2}\d{3}|STOP)$', re.IGNORECASE)
    
    while not stop_event.is_set():
        try:
            # Auto-reconnect logic
            if not bt.is_connected():
                print("[BT Process] Attempting to connect...")
                if not bt.connect():
                    time.sleep(2)  # Retry delay
                    continue
            
            # Receive from Android (obstacle coordinates or STM32 commands) - non-blocking
            data = bt.receive_nonblocking(timeout=0.05)
            if data:
                data_upper = data.strip().upper()
                
                # Check if it's an STM32 command
                if stm32_cmd_pattern.match(data_upper):
                    # Send to Task process for STM32 execution
                    to_task_queue.put(('STM32', data_upper))
                    print(f"[BT Process] STM32 command from Android: {data_upper}")
                else:
                    # Forward to Algorithm process (obstacle coords, etc.)
                    to_algo_queue.put(data)
                    print(f"[BT Process] Data from Android → Algo: {data}")
            
            # Send image rec results to Android
            if not from_task_queue.empty():
                result = from_task_queue.get_nowait()
                print(f"[BT Process] Sending to Android: {result}")
                bt.send(str(result))
            
            # Send algorithm commands to Android (for visibility)
            if not from_algo_queue.empty():
                algo_msg = from_algo_queue.get_nowait()
                print(f"[BT Process] Algo commands → Android: {str(algo_msg)[:100]}...")
                bt.send(str(algo_msg))
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f"[BT Process] Error: {e}")
            # Keep server alive for reconnection
            bt.disconnect(keep_server=True)
            time.sleep(1)
    
    # Cleanup - shut down server completely
    bt.disconnect(keep_server=False)
    print("[BT Process] Stopped")


# =============================================================================
# Process 2: Task (Image Recognition PC Communication)
# =============================================================================
def task_process(
    task_num: int,
    to_bt_queue: Queue,        # Send image rec results to Bluetooth
    from_algo_queue: Queue,    # Receive path from Algorithm
    from_bt_queue: Queue,      # Receive STM32 commands from Bluetooth
    stop_event: Event,
    config: Config,
    mode: str = "hardcoded"    # "hardcoded" or "algorithm"
):
    """
    Task process - handles Image Rec PC communication (stream + results)
    and executes STM32 commands from Algorithm PC.
    
    Args:
        mode: "hardcoded" - use IMAGE_COMMANDS dict for movements
              "algorithm" - execute STM32 commands from Algorithm process
    """
    # Import here for multiprocessing spawn compatibility
    from tasks.task1_rpi import Task1RPI
    from tasks.task2_rpi import Task2RPI
    
    print(f"[Task Process] Starting Task {task_num} in {mode} mode...")
    
    if task_num == 1:
        task = Task1RPI(config, mode=mode)
    else:
        task = Task2RPI(config)
    
    # Set up callback to forward image detections to Bluetooth.
    # For normal detections, we wait for the binary (on_image_binary) before
    # sending to BT. Only special non-image cases (FIN, TIMEOUT, SKIPPED) are
    # sent immediately here.
    def on_image_detected(obstacle_id, image_id, confidence):
        if image_id in ("FIN", "TIMEOUT", "SKIPPED"):
            result = f"TARGET,{obstacle_id},{image_id}"
            print(f"[Task Process] → BT: {result}")
            to_bt_queue.put(result)
        # For normal detections, wait for on_image_binary to fire (which has the frame)
    
    # Set up callback to forward the combined detection + image binary to Bluetooth.
    # Format: IMG,<obstacle_id>,<image_id>,<base64_jpeg>
    def on_image_binary(obstacle_id, image_id, b64_jpeg):
        bt_msg = f"IMG,{obstacle_id},{image_id},{b64_jpeg}"
        print(f"[Task Process] → BT: IMG,{obstacle_id},{image_id},<{len(b64_jpeg)} b64 chars>")
        to_bt_queue.put(bt_msg)
    
    if hasattr(task, 'on_image_detected'):
        task.on_image_detected = on_image_detected
    if hasattr(task, 'on_image_binary'):
        task.on_image_binary = on_image_binary
    
    task.initialize()
    
    try:
        while not stop_event.is_set():
            # Check for STM32 commands from Bluetooth (manual control)
            if not from_bt_queue.empty():
                bt_msg = from_bt_queue.get_nowait()
                if isinstance(bt_msg, tuple) and bt_msg[0] == 'STM32':
                    stm32_cmd = bt_msg[1]
                    print(f"[Task Process] Manual STM32 from BT: {stm32_cmd}")
                    if hasattr(task, 'send_command'):
                        response = task.send_command(stm32_cmd)
                        if response:
                            to_bt_queue.put(f"STM32:{response}")
            
            # Check for path/commands from Algorithm
            if not from_algo_queue.empty():
                path_data = from_algo_queue.get_nowait()
                print(f"[Task Process] Received from Algo: {type(path_data)}")
                
                if hasattr(task, 'execute_path'):
                    # execute_path handles both new format (dict with "commands")
                    # and legacy format (list of waypoints)
                    task.execute_path(path_data)
            
            stop_event.wait(timeout=0.1)
            
    except KeyboardInterrupt:
        pass
    finally:
        task.stop()
        print(f"[Task Process] Task {task_num} stopped")


# =============================================================================
# Process 3: Algorithm (Path Planning PC Communication)
# =============================================================================
def algorithm_process(
    from_bt_queue: Queue,      # Receive obstacle coords from Bluetooth
    to_task_queue: Queue,      # Send path/commands to Task
    to_bt_queue: Queue,        # Send commands to Bluetooth (for Android visibility)
    stop_event: Event,
    config: Config
):
    """
    Algorithm process - handles Algorithm PC communication.
    
    Flow:
    1. Receives obstacle coordinates from Bluetooth (via Android)
    2. Forwards to Algorithm PC
    3. Receives STM32 commands back: {"commands": [...], "path": [...]}
    4. Puts parsed commands into to_task_queue for Task process
    5. Sends commands to Bluetooth for Android visibility
    """
    # Import here for multiprocessing spawn compatibility
    from communication.algo_pc import AlgoPC
    import json
    
    print("[Algo Process] Starting...")
    
    # Initialize Algorithm PC server
    algo = AlgoPC()
    if not algo.start_server():
        print("[Algo Process] Failed to start server")
        return
    
    # Wait for Algorithm PC to connect (with auto-reconnect)
    while not stop_event.is_set():
        try:
            # Auto-reconnect logic
            if not algo.is_connected():
                print("[Algo Process] Waiting for Algorithm PC to connect...")
                if not algo.wait_for_connection(timeout=10.0):
                    time.sleep(2)  # Retry delay
                    continue
            
            # Receive obstacle coords from Bluetooth (from Android)
            if not from_bt_queue.empty():
                coords = from_bt_queue.get_nowait()
                print(f"[Algo Process] Received coords: {coords}")
                
                # Send coords to Algorithm PC (as JSON if dict, else string)
                if algo.is_connected():
                    if isinstance(coords, dict):
                        algo.send_json(coords)
                    elif isinstance(coords, str):
                        # Try to parse string as JSON first
                        try:
                            data = json.loads(coords)
                            algo.send_json(data)
                        except json.JSONDecodeError:
                            algo.send(str(coords))
                    else:
                        algo.send(str(coords))
                    
                    # Receive path/commands from Algorithm PC
                    # Use longer timeout since path calculation can take time
                    response = algo.receive(timeout=40.0)
                    if response:
                        print(f"[Algo Process] Received from Algo PC: {response[:200]}...")
                        
                        # Parse JSON response
                        try:
                            path_data = json.loads(response)
                            print(f"[Algo Process] Parsed path data with keys: {list(path_data.keys()) if isinstance(path_data, dict) else 'list'}")
                            to_task_queue.put(path_data)
                            
                            # Forward commands to Bluetooth for Android visibility
                            if isinstance(path_data, dict) and "commands" in path_data:
                                commands = path_data["commands"]
                                to_bt_queue.put(f"COMMANDS:{json.dumps(commands)}")
                                print(f"[Algo Process] Sent {len(commands)} commands to BT")
                        except json.JSONDecodeError:
                            print(f"[Algo Process] Non-JSON response, forwarding as string")
                            to_task_queue.put(response)
                    else:
                        print("[Algo Process] No response from Algo PC")
            
            stop_event.wait(timeout=0.1)
            
        except Exception as e:
            print(f"[Algo Process] Error: {e}")
            algo.disconnect(keep_server=True)
            time.sleep(1)
    
    # Cleanup
    algo.disconnect(keep_server=False)
    print("[Algo Process] Stopped")


# =============================================================================
# Bluetooth Only Test Mode
# =============================================================================
def run_bluetooth_test():
    """
    Run Bluetooth communication test only.
    Tests 2-way communication between RPi and Android.
    """
    from communication.bluetooth import BluetoothHandler
    
    print("\n" + "=" * 60)
    print("BLUETOOTH 2-WAY COMMUNICATION TEST")
    print("=" * 60)
    
    bt = BluetoothHandler()
    
    print("\n[1] Waiting for Android connection...")
    if not bt.connect():
        print("Failed to connect. Exiting.")
        return
    
    print("\n[2] Connection established!")
    print("=" * 60)
    print("Test Commands:")
    print("  send <msg>  - Send message to Android")
    print("  status      - Show connection status")
    print("  q           - Quit test")
    print("=" * 60)
    print("Note: Auto-reconnects when client disconnects")
    print("=" * 60)
    
    running = True
    
    def bluetooth_connection_thread():
        """Background thread to handle Bluetooth reconnections."""
        while running:
            try:
                if not bt.is_connected():
                    time.sleep(2)  # Wait a bit before trying to reconnect
                    if running and not bt.is_connected():
                        print("\n[Bluetooth] Attempting reconnection...")
                        print(">> ", end='', flush=True)
                        if bt.connect():
                            print("\n[Bluetooth] ✓ Client reconnected!")
                            print(">> ", end='', flush=True)
                else:
                    time.sleep(1)
            except:
                if running:
                    time.sleep(1)
                    continue
                break
    
    def receive_thread():
        """Background thread to receive messages"""
        while running:
            try:
                if not bt.is_connected():
                    time.sleep(0.5)
                    continue
                msg = bt.receive_nonblocking(timeout=0.1)
                if msg:
                    print(f"\n[RECEIVED from Android] >>> {msg}")
                    # Auto-echo to confirm receipt
                    bt.send(f"RPi ACK: {msg}")
                    print(">> ", end='', flush=True)
                elif not bt.is_connected():
                    # Connection lost
                    print("\n[DISCONNECTED] Client disconnected - will auto-reconnect")
                    print(">> ", end='', flush=True)
            except:
                if running:
                    continue
                break
    
    # Start background threads
    bt_conn_thread = threading.Thread(target=bluetooth_connection_thread, daemon=True)
    bt_conn_thread.start()
    
    recv_thread = threading.Thread(target=receive_thread, daemon=True)
    recv_thread.start()
    
    try:
        while running:
            cmd = input(">> ").strip()
            
            if cmd.lower() == 'q':
                break
            elif cmd.lower() == 'status':
                status = "Connected" if bt.is_connected() else "Disconnected (reconnecting...)"
                print(f"Status: {status}")
            elif cmd.lower().startswith('send '):
                msg = cmd[5:]
                if not bt.is_connected():
                    print("[WARN] Not connected. Message will not be sent.")
                elif bt.send(msg):
                    print(f"[SENT to Android] <<< {msg}")
                else:
                    print("[ERROR] Failed to send")
            elif cmd:
                # Treat any other input as a message to send
                if not bt.is_connected():
                    print("[WARN] Not connected. Message will not be sent.")
                elif bt.send(cmd):
                    print(f"[SENT to Android] <<< {cmd}")
                else:
                    print("[ERROR] Failed to send")
                    
    except KeyboardInterrupt:
        print("\n\nInterrupted")
    finally:
        running = False
        bt.disconnect(keep_server=False)
        print("\n[Test] Bluetooth test ended")


# =============================================================================
# Bluetooth + STM32 Test Mode (Mode 3)
# =============================================================================
def run_bluetooth_stm32_test():
    """
    Mode 3: Bluetooth + STM32 bridge test.
    - Receives commands from Android/PC via Bluetooth
    - Forwards them directly to STM32 over serial
    - Sends STM32 response back via Bluetooth
    - Keyboard input can also send commands manually
    """
    from communication.bluetooth import BluetoothHandler
    from communication.stm32 import STM32
    import re

    print("\n" + "=" * 60)
    print("BLUETOOTH + STM32 BRIDGE TEST")
    print("=" * 60)

    # --- Connect STM32 ---
    stm = STM32()
    ports_to_try = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyAMA0"]
    stm32_ok = False
    for port in ports_to_try:
        stm.port = port
        if stm.connect():
            stm32_ok = True
            break

    if not stm32_ok:
        print("[Mode 3] ⚠ STM32 not connected. Commands will be echoed only.")
        print("[Mode 3]   Check USB cable and run: ls /dev/tty*")

    # --- Initialize Bluetooth (non-blocking) ---
    bt = BluetoothHandler()
    
    print("\n[Mode 3] Starting Bluetooth server in background...")
    print("=" * 60)
    print("You can start sending STM32 commands immediately.")
    print("Bluetooth will connect when a client connects.")
    print("=" * 60)
    print("Keyboard commands:")
    print("  send <cmd>  - Send STM32 command manually (e.g. send SF050)")
    print("  msg <text>  - Send message to PC/Android (e.g. msg Hello)")
    print("  status      - Show connection status")
    print("  q           - Quit")
    print("=" * 60)

    stm32_cmd_pattern = re.compile(r'^([A-Z]{2}\d{3}|STOP)$', re.IGNORECASE)
    running = True

    def bluetooth_connection_thread():
        """Background thread to handle Bluetooth connections."""
        while running:
            try:
                if not bt.is_connected():
                    print("\n[Bluetooth] Waiting for client connection...")
                    print(">> ", end='', flush=True)
                    if bt.connect():
                        print("\n[Bluetooth] ✓ Client connected!")
                        print(">> ", end='', flush=True)
                else:
                    time.sleep(1)
            except:
                if running:
                    time.sleep(1)
                    continue
                break

    def receive_thread():
        """Receive from Bluetooth, forward to STM32."""
        while running:
            try:
                if not bt.is_connected():
                    time.sleep(0.5)
                    continue
                msg = bt.receive_nonblocking(timeout=0.1)
                if msg:
                    msg = msg.strip()
                    print(f"\n[BT → RPi] {msg}")

                    if stm32_ok and stm32_cmd_pattern.match(msg.upper()):
                        # Forward to STM32
                        sent = stm.send(msg.upper())
                        response = stm.receive(timeout=2.0) if sent else None
                        if response:
                            print(f"[STM32 → RPi] {response}")
                            bt.send(f"STM32:{response}")
                            print(f"[RPi → BT] STM32:{response}")
                        else:
                            bt.send(f"ACK:{msg.upper()}")
                            print(f"[RPi → BT] ACK:{msg.upper()}")
                    else:
                        # Not a STM32 command — echo back
                        bt.send(f"RPi ACK: {msg}")
                        print(f"[RPi → BT] RPi ACK: {msg}")

                    print(">> ", end='', flush=True)
                elif not bt.is_connected():
                    # Connection lost
                    print("\n[DISCONNECTED] Client disconnected")
                    print(">> ", end='', flush=True)
            except:
                if running:
                    continue
                break

    # Start background threads
    bt_conn_thread = threading.Thread(target=bluetooth_connection_thread, daemon=True)
    bt_conn_thread.start()
    
    recv_thread = threading.Thread(target=receive_thread, daemon=True)
    recv_thread.start()

    try:
        while running:
            cmd = input(">> ").strip()

            if cmd.lower() == 'q':
                break
            elif cmd.lower() == 'status':
                print(f"  Bluetooth : {'Connected' if bt.is_connected() else 'Waiting for connection...'}")
                print(f"  STM32     : {'Connected' if stm32_ok and stm.connected else 'Not connected'}")
            elif cmd.lower().startswith('msg '):
                message = cmd[4:].strip()
                if not bt.is_connected():
                    print("[WARN] Bluetooth not connected. Message not sent.")
                elif bt.send(message):
                    print(f"[RPi → BT] {message}")
                else:
                    print("[ERROR] Failed to send message")
            elif cmd.lower().startswith('send '):
                raw_cmd = cmd[5:].strip().upper()
                if stm32_ok:
                    # Send to STM32 regardless of Bluetooth status
                    sent = stm.send(raw_cmd)
                    response = stm.receive(timeout=10.0) if sent else None
                    
                    if response:
                        print(f"[STM32 → RPi] {response}")
                        reply = f"STM32:{response}"
                    else:
                        reply = f"ACK:{raw_cmd}"
                    
                    # Send response over Bluetooth if connected
                    if bt.is_connected():
                        bt.send(reply)
                        print(f"[RPi → BT] {reply}")
                else:
                    print("[WARN] STM32 not connected")
                    # Still send acknowledgment over Bluetooth if connected
                    if bt.is_connected():
                        reply = f"ACK:{raw_cmd} (STM32 not connected)"
                        bt.send(reply)
                        print(f"[RPi → BT] {reply}")
            elif cmd:
                print("Unknown command. Use: send <cmd>, msg <text>, status, q")

    except KeyboardInterrupt:
        print("\n\nInterrupted")
    finally:
        running = False
        bt.disconnect(keep_server=False)
        stm.disconnect()
        print("\n[Test] Bluetooth + STM32 test ended")


# =============================================================================
# Bluetooth + Algorithm PC Bridge Test (Mode 4)
# =============================================================================
def run_bluetooth_algo_bridge():
    """
    Mode 4: Bluetooth + Algorithm PC bridge.
    - Receives data from Android/PC via Bluetooth
    - Forwards to Algorithm PC (connected via RPi AP network)
    - Receives response from Algorithm PC
    - Sends response back via Bluetooth
    """
    from communication.bluetooth import BluetoothHandler
    from communication.algo_pc import AlgoPC

    print("\n" + "=" * 60)
    print("BLUETOOTH + ALGORITHM PC BRIDGE TEST")
    print("=" * 60)

    # --- Start Algorithm PC server (non-blocking) ---
    algo = AlgoPC()
    print("\n[1] Starting Algorithm PC server...")
    if not algo.start_server():
        print("[Mode 4] ✗ Failed to start Algorithm PC server.")
        print("[Mode 4]   Port may already be in use.")
        return
    
    # --- Initialize Bluetooth (non-blocking) ---
    bt = BluetoothHandler()
    
    print("\n[Mode 4] Starting Bluetooth server in background...")
    print("=" * 60)
    print("Bluetooth messages will be forwarded to Algorithm PC.")
    print("Algorithm PC responses will be sent back to Bluetooth.")
    print("=" * 60)
    print("Keyboard commands:")
    print("  msg <text>  - Send message to Bluetooth client")
    print("  algo <text> - Send message to Algorithm PC")
    print("  status      - Show connection status")
    print("  q           - Quit")
    print("=" * 60)

    running = True

    def algo_connection_thread():
        """Background thread to handle Algorithm PC connections."""
        while running:
            try:
                if not algo.is_connected():
                    print("\n[AlgoPC] Waiting for Algorithm PC to connect...")
                    print(">> ", end='', flush=True)
                    if algo.wait_for_connection(timeout=60.0):
                        print("\n[AlgoPC] ✓ Algorithm PC connected!")
                        print(">> ", end='', flush=True)
                else:
                    time.sleep(1)
            except:
                if running:
                    time.sleep(1)
                    continue
                break

    def bluetooth_connection_thread():
        """Background thread to handle Bluetooth connections."""
        while running:
            try:
                if not bt.is_connected():
                    print("\n[Bluetooth] Waiting for client connection...")
                    print(">> ", end='', flush=True)
                    if bt.connect():
                        print("\n[Bluetooth] ✓ Client connected!")
                        print(">> ", end='', flush=True)
                else:
                    time.sleep(1)
            except:
                if running:
                    time.sleep(1)
                    continue
                break

    def receive_bluetooth_thread():
        """Receive from Bluetooth, forward to Algorithm PC."""
        while running:
            try:
                if not bt.is_connected():
                    time.sleep(0.5)
                    continue
                
                msg = bt.receive_nonblocking(timeout=0.1)
                if msg:
                    msg = msg.strip()
                    print(f"\n[BT → RPi] {msg}")

                    if algo.is_connected():
                        # Forward to Algorithm PC
                        try:
                            # Try to parse as JSON first
                            import json
                            data = json.loads(msg)
                            algo.send_json(data)
                            print(f"[RPi → AlgoPC] {msg} (JSON)")
                        except json.JSONDecodeError:
                            # Send as plain text
                            algo.send(msg)
                            print(f"[RPi → AlgoPC] {msg}")
                        
                        # Note: Response from Algo PC will be handled by receive_algopc_thread
                    else:
                        # Algorithm PC not connected - just acknowledge
                        ack = f"ACK:{msg} (AlgoPC not connected)"
                        bt.send(ack)
                        print(f"[RPi → BT] {ack}")

                    print(">> ", end='', flush=True)
                elif not bt.is_connected():
                    # Connection lost
                    print("\n[DISCONNECTED] Bluetooth client disconnected")
                    print(">> ", end='', flush=True)
            except Exception as e:
                if running:
                    print(f"\n[BT Error] {e}")
                    print(">> ", end='', flush=True)
                    continue
                break

    def receive_algopc_thread():
        """Receive from Algorithm PC, forward to Bluetooth."""
        while running:
            try:
                if not algo.is_connected():
                    time.sleep(0.5)
                    continue
                
                # Receive message from Algorithm PC (non-blocking with timeout)
                msg = algo.receive(timeout=0.1)
                if msg:
                    msg = msg.strip()
                    print(f"\n[AlgoPC → RPi] {msg}")
                    
                    if bt.is_connected():
                        # Forward to Bluetooth
                        bt.send(msg)
                        print(f"[RPi → BT] {msg}")
                    else:
                        print("[RPi] Bluetooth not connected - message not forwarded")
                    
                    print(">> ", end='', flush=True)
                elif not algo.is_connected():
                    # Connection lost
                    print("\n[DISCONNECTED] Algorithm PC disconnected")
                    print(">> ", end='', flush=True)
                    time.sleep(1)
                    
            except Exception as e:
                if running and algo.is_connected():
                    # Only log if we're still supposed to be connected
                    print(f"\n[AlgoPC Error] {e}")
                    print(">> ", end='', flush=True)
                time.sleep(0.5)

    # Start background threads
    algo_conn_thread = threading.Thread(target=algo_connection_thread, daemon=True)
    algo_conn_thread.start()
    
    bt_conn_thread = threading.Thread(target=bluetooth_connection_thread, daemon=True)
    bt_conn_thread.start()
    
    recv_bt_thread = threading.Thread(target=receive_bluetooth_thread, daemon=True)
    recv_bt_thread.start()
    
    recv_algo_thread = threading.Thread(target=receive_algopc_thread, daemon=True)
    recv_algo_thread.start()

    try:
        while running:
            cmd = input(">> ").strip()

            if cmd.lower() == 'q':
                break
            elif cmd.lower() == 'status':
                print(f"  Bluetooth : {'Connected' if bt.is_connected() else 'Waiting for connection...'}")
                print(f"  AlgoPC    : {'Connected' if algo.is_connected() else 'Waiting for connection...'}")
            elif cmd.lower().startswith('msg '):
                message = cmd[4:].strip()
                if not bt.is_connected():
                    print("[WARN] Bluetooth not connected. Message not sent.")
                elif bt.send(message):
                    print(f"[RPi → BT] {message}")
                else:
                    print("[ERROR] Failed to send message")
            elif cmd.lower().startswith('algo '):
                message = cmd[5:].strip()
                if not algo.is_connected():
                    print("[WARN] Algorithm PC not connected. Message not sent.")
                else:
                    try:
                        algo.send(message)
                        print(f"[RPi → AlgoPC] {message}")
                        response = algo.receive(timeout=5.0)
                        if response:
                            print(f"[AlgoPC → RPi] {response}")
                        else:
                            print("[AlgoPC] No response")
                    except Exception as e:
                        print(f"[ERROR] Failed to communicate with AlgoPC: {e}")
            elif cmd:
                print("Unknown command. Use: msg <text>, algo <text>, status, q")

    except KeyboardInterrupt:
        print("\n\nInterrupted")
    finally:
        running = False
        bt.disconnect(keep_server=False)
        algo.disconnect(keep_server=False)
        print("\n[Test] Bluetooth + Algorithm PC bridge test ended")


# =============================================================================
# Image Rec PC Communication Test (Mode 5)
# =============================================================================
def run_imgrec_pc_test():
    """
    Mode 5: Image Recognition PC communication test.
    - Starts video stream server (UDP) for PC to receive video
    - Waits for Image Rec PC to connect (TCP)
    - Receives and prints all detection results from PC
    - Tests the communication path: RPi → PC (video) and PC → RPi (detections)
    """
    from tasks.task5_rpi import Task5RPI
    from config.config import get_config

    print("\n" + "=" * 60)
    print("IMAGE RECOGNITION PC COMMUNICATION TEST")
    print("=" * 60)
    print("\nThis test will:")
    print("  1. Start video stream server (UDP)")
    print("  2. Wait for Image Rec PC to connect (TCP)")
    print("  3. Print all detection results from PC")
    print("\nExpected message formats from PC:")
    print("  - Detection: 'obstacle_id,confidence,image_id'")
    print("  - No detection: 'NONE'")
    print("  - Commands: 'SEEN', 'STITCH'")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)

    config = get_config()
    task5 = Task5RPI(config)
    running = True

    def message_monitor():
        """Background thread to show live stats"""
        last_count = 0
        while running:
            if task5.message_count > last_count:
                last_count = task5.message_count
            time.sleep(2)

    try:
        # Initialize Task5
        task5.initialize()
        
        if not task5.running:
            print("\n[Mode 5] Failed to initialize. Exiting.")
            return
        
        # Start monitor thread
        monitor_thread = threading.Thread(target=message_monitor, daemon=True)
        monitor_thread.start()
        
        print("\n" + "=" * 60)
        print("Commands:")
        print("  status  - Show connection and message stats")
        print("  q       - Quit test")
        print("=" * 60)
        print()
        
        # Main loop
        while running:
            try:
                cmd = input(">> ").strip().lower()
                
                if cmd == 'q':
                    break
                elif cmd == 'status':
                    print(f"\n  PC Connected: {task5.pc.connected}")
                    print(f"  Messages Received: {task5.message_count}")
                    print(f"  Last Image: {task5.last_image or 'None'}")
                    print()
                elif cmd:
                    print("Unknown command. Use: status, q")
                    
            except EOFError:
                # Handle case where input is not available (e.g., in background)
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n\n[Mode 5] Interrupted by user")
    finally:
        running = False
        task5.stop()
        print("\n[Mode 5] Image Rec PC communication test ended")
        print(f"[Mode 5] Total messages received: {task5.message_count}")


# =============================================================================
# Full Integration Test (Mode 6)
# =============================================================================
def run_full_integration_test():
    """
    Mode 6: Full integration simulation - BT + Algo PC + Image Rec PC (no STM32)
    
    Same pipeline as Mode 1 but without STM32 hardware:
    1. BT → RPi → Algo PC (obstacle coordinates)
    2. Algo PC → RPi (STM32 commands as JSON)
    3. RPi simulates STM32 commands (prints instead of serial send)
    4. At SNAP commands: waits for Image Rec PC detection before continuing
    5. Detection results forwarded to BT (Android)
    
    Use this to test the full pipeline by showing images to the camera manually.
    """
    from communication.bluetooth import BluetoothHandler
    from communication.algo_pc import AlgoPC
    from communication.pc import PC
    from camera.stream_server import StreamServer
    from config.config import get_config
    from queue import Queue, Empty
    import json

    print("\n" + "=" * 60)
    print("FULL INTEGRATION SIMULATION (BT + ALGO + IMG REC)")
    print("No STM32 - commands are printed, SNAP waits for detection")
    print("=" * 60)
    print("\nNote: If Bluetooth fails to connect:")
    print("  Run: sudo rfcomm release all")
    print("  Or restart bluetooth: sudo systemctl restart bluetooth")
    print("=" * 60)
    
    config = get_config()
    
    # Initialize all communication handlers
    bt = BluetoothHandler()
    algo = AlgoPC()
    imgpc = PC()
    
    # Detection queue: receive_imgpc_thread puts detections here,
    # command executor reads from here when waiting at SNAP
    detection_queue = Queue()
    
    # Execution state
    executing_commands = False
    
    # Start Algorithm PC server
    print("\n[1] Starting Algorithm PC server...")
    if not algo.start_server():
        print("[Mode 6] Failed to start Algorithm PC server.")
        return
    
    # Start video stream server in background thread
    print("[2] Starting video stream server...")
    def run_stream():
        try:
            StreamServer().start(
                framerate=15,
                quality=45,
                is_outdoors=config.is_outdoors
            )
        except Exception as e:
            print(f"[Stream] Error: {e}")
    
    stream_thread = threading.Thread(target=run_stream, daemon=True)
    stream_thread.start()
    time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("System Status:")
    print("  - Video Stream: Running (UDP port 5005)")
    print("  - Image Rec PC: Waiting for connection (TCP port 5000)")
    print("  - Algo PC: Waiting for connection (TCP port 6000)")
    print("  - Bluetooth: Waiting for connection")
    print("  - STM32: DISABLED (simulation mode)")
    print("=" * 60)
    print("\nKeyboard commands:")
    print("  status      - Show all connection status")
    print("  bt <text>   - Send message to Bluetooth")
    print("  algo <text> - Send message to Algo PC")
    print("  q           - Quit")
    print("=" * 60)
    
    running = True
    msg_count = {'bt': 0, 'algo': 0, 'imgpc': 0}
    DETECTION_TIMEOUT = 60.0  # seconds to wait for detection at each obstacle
    
    def algo_connection_thread():
        """Handle Algo PC connections"""
        while running:
            try:
                if not algo.is_connected():
                    print("\n[AlgoPC] Waiting for Algorithm PC to connect...")
                    print(">> ", end='', flush=True)
                    if algo.wait_for_connection(timeout=60.0):
                        print("\n[AlgoPC] ✓ Algorithm PC connected!")
                        print(">> ", end='', flush=True)
                else:
                    time.sleep(1)
            except Exception as e:
                if running:
                    print(f"\n[AlgoPC Thread Error] {e}")
                    print(">> ", end='', flush=True)
                    time.sleep(1)
                else:
                    break

    def imgpc_connection_thread():
        """Handle Image Rec PC connection in background (non-blocking)"""
        while running:
            try:
                if not imgpc.connected:
                    print("\n[ImgPC] Waiting for Image Rec PC to connect (TCP port 5000)...")
                    print(">> ", end='', flush=True)
                    imgpc.connect()
                    if imgpc.connected:
                        print("\n[ImgPC] ✓ Image Rec PC connected!")
                        print(">> ", end='', flush=True)
                        # Start receive thread now that PC is connected
                        t = threading.Thread(target=receive_imgpc_thread, daemon=True)
                        t.start()
                        # Wait for receive thread to exit (ImgPC disconnected), then loop back
                        t.join()
                        imgpc.connected = False
                        print("\n[ImgPC] Disconnected, waiting for reconnect...")
                        print(">> ", end='', flush=True)
                else:
                    time.sleep(1)
            except Exception as e:
                if running:
                    print(f"\n[ImgPC Thread Error] {e}")
                    print(">> ", end='', flush=True)
                    time.sleep(2)
                else:
                    break
    
    def bluetooth_connection_thread():
        """Handle Bluetooth connections"""
        while running:
            try:
                if not bt.is_connected():
                    print("\n[Bluetooth] Waiting for client connection...")
                    print(">> ", end='', flush=True)
                    if bt.connect():
                        print("\n[Bluetooth] ✓ Client connected!")
                        print(">> ", end='', flush=True)
                else:
                    time.sleep(1)
            except Exception as e:
                if running:
                    print(f"\n[Bluetooth Thread Error] {e}")
                    print(">> ", end='', flush=True)
                    time.sleep(1)
                else:
                    break
    
    def receive_bluetooth_thread():
        """Receive from BT, forward obstacle coords to Algo PC"""
        while running:
            try:
                if not bt.is_connected():
                    time.sleep(0.5)
                    continue
                
                msg = bt.receive_nonblocking(timeout=0.1)
                if msg:
                    msg = msg.strip()
                    msg_count['bt'] += 1
                    print(f"\n[BT → RPi] {msg}")
                    
                    # Forward to Algorithm PC (obstacle coordinates)
                    if algo.is_connected():
                        try:
                            data = json.loads(msg)
                            algo.send_json(data)
                            print(f"[RPi → AlgoPC] {msg} (JSON)")
                        except json.JSONDecodeError:
                            algo.send(msg)
                            print(f"[RPi → AlgoPC] {msg}")
                    else:
                        print("[RPi] AlgoPC not connected - message not forwarded")
                    
                    print(">> ", end='', flush=True)
                elif not bt.is_connected():
                    print("\n[DISCONNECTED] Bluetooth client disconnected")
                    print(">> ", end='', flush=True)
            except Exception as e:
                if running:
                    print(f"\n[BT Error] {e}")
                    print(">> ", end='', flush=True)
                time.sleep(0.5)
    
    def execute_commands_simulated(commands):
        """
        Execute STM32 commands in simulation mode (no STM32 hardware).
        
        - Movement commands (FW/BW/BL/BR): printed to console
        - SNAP commands: sent to ImgPC, blocks until detection received
        - FIN: prints completion
        
        Args:
            commands: List of STM32 command strings from Algo PC
        """
        nonlocal executing_commands
        executing_commands = True
        total = len(commands)
        
        print(f"\n{'='*60}")
        print(f"[SIM] Starting simulated execution: {total} commands")
        print(f"[SIM] Commands: {commands}")
        print(f"{'='*60}\n")
        
        for i, cmd in enumerate(commands):
            if not running or not executing_commands:
                print("[SIM] Execution stopped")
                break
            
            cmd = cmd.strip()
            
            # ---- FIN: Done ----
            if cmd == "FIN":
                print(f"\n[SIM] [{i+1}/{total}] FIN - All obstacles visited!")
                if bt.is_connected():
                    bt.send("TARGET,DONE,FIN")
                    print("[RPi → BT] TARGET,DONE,FIN")
                break
            
            # ---- SNAP: Image detection (blocking) ----
            if cmd.startswith("SNAP"):
                # Parse obstacle ID: "SNAP3_C" → obstacle_id="3", position="C"
                snap_body = cmd[4:]  # "3_C"
                parts = snap_body.split("_")
                obstacle_id = parts[0]
                position = parts[1] if len(parts) > 1 else "C"
                
                print(f"\n[SIM] [{i+1}/{total}] {cmd}")
                print(f"[SIM] ===== OBSTACLE {obstacle_id} =====")
                print(f"[SIM] Show an image to the camera now!")
                print(f"[SIM] Waiting for Image Rec PC detection (timeout: {DETECTION_TIMEOUT}s)...")
                
                # Clear stale detections
                while not detection_queue.empty():
                    try:
                        stale = detection_queue.get_nowait()
                        print(f"[SIM] Discarding stale detection: {stale}")
                    except Empty:
                        break
                
                # Send SNAP command to Image Rec PC
                if imgpc.connected:
                    imgpc.send(cmd)
                    print(f"[RPi → ImgPC] {cmd}")
                else:
                    print("[SIM] WARNING: ImgPC not connected! Skipping detection...")
                    continue
                
                # Block and wait for detection result
                try:
                    detection = detection_queue.get(timeout=DETECTION_TIMEOUT)
                    det_obs = detection.get('obstacle_id', '?')
                    det_img = detection.get('image_id', '?')
                    det_conf = detection.get('confidence', '?')
                    
                    print(f"[SIM] ✓ DETECTED: obstacle={det_obs}, image={det_img}, conf={det_conf}")
                    
                    # Forward to Bluetooth (Android)
                    if bt.is_connected():
                        result_msg = f"TARGET,{obstacle_id},{det_img}"
                        bt.send(result_msg)
                        print(f"[RPi → BT] {result_msg}")
                    
                    print(f"[SIM] ===== OBSTACLE {obstacle_id} DONE =====")
                    
                except Empty:
                    print(f"[SIM] ⚠ TIMEOUT waiting for detection of obstacle {obstacle_id}!")
                    if bt.is_connected():
                        bt.send(f"TARGET,{obstacle_id},TIMEOUT")
                
                continue
            
            # ---- Movement commands: SF, SB, LF, RF, LB, RB ----
            if cmd.startswith(("SF", "SB", "LF", "RF", "LB", "RB")):
                cmd_type = cmd[:2]
                cmd_val = cmd[2:]
                
                labels = {
                    "SF": "FORWARD", 
                    "SB": "BACKWARD", 
                    "LF": "LEFT FORWARD TURN", 
                    "RF": "RIGHT FORWARD TURN",
                    "LB": "LEFT BACKWARD TURN",
                    "RB": "RIGHT BACKWARD TURN"
                }
                label = labels.get(cmd_type, cmd_type)
                
                if cmd_type in ("SF", "SB"):
                    print(f"[SIM] [{i+1}/{total}] {cmd} → {label} {cmd_val}cm")
                else:
                    print(f"[SIM] [{i+1}/{total}] {cmd} → {label} {cmd_val}°")
                
                # Simulate movement delay
                time.sleep(0.3)
                print(f"[SIM] ← ACK (simulated)")
                continue
            
            # ---- Unknown command ----
            print(f"[SIM] [{i+1}/{total}] Unknown command: {cmd}")
        
        executing_commands = False
        print(f"\n{'='*60}")
        print("[SIM] Simulated execution complete")
        print(f"{'='*60}")
        print(">> ", end='', flush=True)
    
    def receive_algopc_thread():
        """Receive from Algo PC, parse commands, execute in simulation"""
        while running:
            try:
                if not algo.is_connected():
                    time.sleep(0.5)
                    continue
                
                msg = algo.receive(timeout=0.1)
                if msg:
                    msg = msg.strip()
                    msg_count['algo'] += 1
                    print(f"\n[AlgoPC → RPi] {msg[:200]}{'...' if len(msg) > 200 else ''}")
                    
                    # Try to parse as JSON with commands
                    try:
                        data = json.loads(msg)
                        if isinstance(data, dict) and "commands" in data:
                            commands = data["commands"]
                            print(f"[Mode 6] Received {len(commands)} STM32 commands from Algo PC")
                            
                            # Forward raw response to BT for visibility
                            if bt.is_connected():
                                bt.send(f"COMMANDS:{json.dumps(commands)}")
                            
                            # Guard: don't start a second executor while one is running
                            if executing_commands:
                                print("[Mode 6] WARNING: Already executing commands, ignoring new path")
                            else:
                                exec_thread = threading.Thread(
                                    target=execute_commands_simulated,
                                    args=(commands,),
                                    daemon=True
                                )
                                exec_thread.start()
                        elif isinstance(data, list):
                            # Legacy format (list of commands or waypoints)
                            if data and isinstance(data[0], str):
                                print(f"[Mode 6] Received {len(data)} commands (list format)")
                                if executing_commands:
                                    print("[Mode 6] WARNING: Already executing commands, ignoring new path")
                                else:
                                    exec_thread = threading.Thread(
                                        target=execute_commands_simulated,
                                        args=(data,),
                                        daemon=True
                                    )
                                    exec_thread.start()
                            else:
                                print("[Mode 6] Received raw path (legacy) - forwarding to BT")
                                if bt.is_connected():
                                    bt.send(msg)
                        else:
                            # Other JSON - just forward to BT
                            if bt.is_connected():
                                bt.send(msg)
                                print(f"[RPi → BT] {msg}")
                    except json.JSONDecodeError:
                        # Plain text - forward to BT
                        if bt.is_connected():
                            bt.send(msg)
                            print(f"[RPi → BT] {msg}")
                    
                    print(">> ", end='', flush=True)
                elif not algo.is_connected():
                    print("\n[DISCONNECTED] Algorithm PC disconnected")
                    print(">> ", end='', flush=True)
                    time.sleep(1)
            except Exception as e:
                if running and algo.is_connected():
                    print(f"\n[AlgoPC Error] {e}")
                    print(">> ", end='', flush=True)
                time.sleep(0.5)
    
    def receive_imgpc_thread():
        """Receive from Image Rec PC, put detections into queue for executor"""
        while running:
            try:
                if not imgpc.connected:
                    time.sleep(0.5)
                    continue
                
                msg = imgpc.receive()
                if msg:
                    msg = msg.strip()
                    msg_count['imgpc'] += 1
                    timestamp = time.strftime("%H:%M:%S")
                    
                    # Parse detection result: "obstacle_id,confidence,image_id"
                    if "," in msg and len(msg.split(",")) == 3:
                        obstacle_id, conf, image_id = msg.split(",")
                        confidence = None
                        try:
                            confidence = float(conf)
                        except ValueError:
                            pass
                        
                        print(f"\n[{timestamp}] Image Detection:")
                        print(f"  Obstacle: {obstacle_id} | Image: {image_id} | Conf: {conf}")
                        
                        # Put into detection queue for command executor
                        detection_queue.put({
                            'obstacle_id': obstacle_id,
                            'image_id': image_id,
                            'confidence': confidence
                        })
                        
                        # Also forward to BT if NOT currently executing
                        # (during execution, the executor handles BT forwarding)
                        if not executing_commands and bt.is_connected():
                            forward_msg = f"IMG:{msg}"
                            bt.send(forward_msg)
                            print(f"[RPi → BT] {forward_msg}")
                    else:
                        print(f"\n[{timestamp}] ImgPC → RPi: {msg}")
                        if bt.is_connected():
                            bt.send(f"IMG:{msg}")
                    
                    print(">> ", end='', flush=True)
            except Exception as e:
                if running:
                    print(f"\n[ImgPC Error] {e}")
                    print(">> ", end='', flush=True)
                    imgpc.connected = False
                break
    
    # Start all background threads
    algo_conn_thread = threading.Thread(target=algo_connection_thread, daemon=True)
    algo_conn_thread.start()
    
    bt_conn_thread = threading.Thread(target=bluetooth_connection_thread, daemon=True)
    bt_conn_thread.start()
    
    recv_bt_thread = threading.Thread(target=receive_bluetooth_thread, daemon=True)
    recv_bt_thread.start()
    
    recv_algo_thread = threading.Thread(target=receive_algopc_thread, daemon=True)
    recv_algo_thread.start()
    
    imgpc_conn_thread = threading.Thread(target=imgpc_connection_thread, daemon=True)
    imgpc_conn_thread.start()
    
    # Main command loop
    try:
        while running:
            cmd = input(">> ").strip()
            
            if cmd.lower() == 'q':
                break
            elif cmd.lower() == 'status':
                print(f"\n  Bluetooth  : {'Connected' if bt.is_connected() else 'Waiting...'}")
                print(f"  AlgoPC     : {'Connected' if algo.is_connected() else 'Waiting...'}")
                print(f"  ImgPC      : {'Connected' if imgpc.connected else 'Not connected'}")
                print(f"  Stream     : Running")
                print(f"  STM32      : DISABLED (simulation)")
                print(f"  Executing  : {'Yes' if executing_commands else 'No'}")
                print(f"\n  Messages Received:")
                print(f"    BT → RPi    : {msg_count['bt']}")
                print(f"    AlgoPC → RPi: {msg_count['algo']}")
                print(f"    ImgPC → RPi : {msg_count['imgpc']}")
                print()
            elif cmd.lower().startswith('bt '):
                message = cmd[3:].strip()
                if bt.is_connected():
                    bt.send(message)
                    print(f"[RPi → BT] {message}")
                else:
                    print("[WARN] Bluetooth not connected")
            elif cmd.lower().startswith('algo '):
                message = cmd[5:].strip()
                if algo.is_connected():
                    algo.send(message)
                    print(f"[RPi → AlgoPC] {message}")
                else:
                    print("[WARN] Algo PC not connected")
            elif cmd:
                print("Unknown command. Use: status, bt <text>, algo <text>, q")
    
    except KeyboardInterrupt:
        print("\n\n[Mode 6] Interrupted by user")
    finally:
        running = False
        executing_commands = False
        bt.disconnect(keep_server=False)
        algo.disconnect(keep_server=False)
        imgpc.disconnect()
        print("\n[Mode 6] Full integration simulation ended")
        print(f"[Mode 6] Total messages: BT={msg_count['bt']}, Algo={msg_count['algo']}, ImgPC={msg_count['imgpc']}")


# =============================================================================
# STM32 Movement Test (Mode 7)
# =============================================================================
def run_stm32_movement_test():
    """
    Mode 7: BT + Algo PC + STM32 movement test (no camera/image rec)
    
    Same as Mode 6 but:
    - STM32 is ENABLED: movement commands are sent to the real robot
    - Camera/ImgPC is DISABLED: SNAP commands are skipped (just printed)
    
    Purpose: Test if the robot physically moves the correct path from the algorithm.
    
    Flow:
    1. BT → RPi → Algo PC (obstacle coordinates)
    2. Algo PC → RPi (STM32 commands as JSON)
    3. RPi sends movement commands to STM32, waits for ACK
    4. SNAP commands are logged but skipped (no image detection)
    5. FIN → path complete
    """
    from communication.bluetooth import BluetoothHandler
    from communication.algo_pc import AlgoPC
    from communication.stm32 import STM32
    from config.config import get_config
    import json

    print("\n" + "=" * 60)
    print("STM32 MOVEMENT TEST (BT + ALGO + STM32, no camera)")
    print("Robot will physically move the algo path. SNAP = skip.")
    print("=" * 60)
    print("\nNote: If Bluetooth fails to connect:")
    print("  Run: sudo rfcomm release all")
    print("  Or restart bluetooth: sudo systemctl restart bluetooth")
    print("=" * 60)
    
    config = get_config()
    
    # Initialize communication handlers
    bt = BluetoothHandler()
    algo = AlgoPC()
    
    # Initialize STM32
    stm = STM32()
    stm32_ok = False
    ports_to_try = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyAMA0"]
    for port in ports_to_try:
        stm.port = port
        if stm.connect():
            stm32_ok = True
            break
    
    if not stm32_ok:
        print("[Mode 7] ⚠ STM32 not connected! Commands will be printed only.")
        print("[Mode 7]   Check USB cable and run: ls /dev/tty*")
    
    # Execution state
    executing_commands = False
    STM32_ACK_TIMEOUT = 10.0
    
    # Start Algorithm PC server
    print("\n[1] Starting Algorithm PC server...")
    if not algo.start_server():
        print("[Mode 7] Failed to start Algorithm PC server.")
        return
    
    print("\n" + "=" * 60)
    print("System Status:")
    print(f"  - STM32: {'Connected (' + stm.port + ')' if stm32_ok else 'NOT CONNECTED'}")
    print("  - Algo PC: Waiting for connection (TCP port 6000)")
    print("  - Bluetooth: Waiting for connection")
    print("  - Camera/ImgPC: DISABLED (movement test only)")
    print("=" * 60)
    print("\nKeyboard commands:")
    print("  status      - Show all connection status")
    print("  bt <text>   - Send message to Bluetooth")
    print("  algo <text> - Send message to Algo PC")
    print("  stm <cmd>   - Send manual command to STM32 (e.g., stm SF010)")
    print("  q           - Quit")
    print("=" * 60)
    
    running = True
    msg_count = {'bt': 0, 'algo': 0}
    
    def algo_connection_thread():
        """Handle Algo PC connections"""
        while running:
            try:
                if not algo.is_connected():
                    print("\n[AlgoPC] Waiting for Algorithm PC to connect...")
                    print(">> ", end='', flush=True)
                    if algo.wait_for_connection(timeout=60.0):
                        print("\n[AlgoPC] ✓ Algorithm PC connected!")
                        print(">> ", end='', flush=True)
                else:
                    time.sleep(1)
            except Exception as e:
                if running:
                    print(f"\n[AlgoPC Thread Error] {e}")
                    print(">> ", end='', flush=True)
                    time.sleep(1)
                else:
                    break
    
    def bluetooth_connection_thread():
        """Handle Bluetooth connections"""
        while running:
            try:
                if not bt.is_connected():
                    print("\n[Bluetooth] Waiting for client connection...")
                    print(">> ", end='', flush=True)
                    if bt.connect():
                        print("\n[Bluetooth] ✓ Client connected!")
                        print(">> ", end='', flush=True)
                else:
                    time.sleep(1)
            except Exception as e:
                if running:
                    print(f"\n[Bluetooth Thread Error] {e}")
                    print(">> ", end='', flush=True)
                    time.sleep(1)
                else:
                    break
    
    def receive_bluetooth_thread():
        """Receive from BT, forward obstacle coords to Algo PC"""
        while running:
            try:
                if not bt.is_connected():
                    time.sleep(0.5)
                    continue
                
                msg = bt.receive_nonblocking(timeout=0.1)
                if msg:
                    msg = msg.strip()
                    msg_count['bt'] += 1
                    print(f"\n[BT → RPi] {msg}")
                    
                    # Forward to Algorithm PC (obstacle coordinates)
                    if algo.is_connected():
                        try:
                            data = json.loads(msg)
                            algo.send_json(data)
                            print(f"[RPi → AlgoPC] {msg} (JSON)")
                        except json.JSONDecodeError:
                            algo.send(msg)
                            print(f"[RPi → AlgoPC] {msg}")
                    else:
                        print("[RPi] AlgoPC not connected - message not forwarded")
                    
                    print(">> ", end='', flush=True)
                elif not bt.is_connected():
                    print("\n[DISCONNECTED] Bluetooth client disconnected")
                    print(">> ", end='', flush=True)
            except Exception as e:
                if running:
                    print(f"\n[BT Error] {e}")
                    print(">> ", end='', flush=True)
                time.sleep(0.5)
    
    def execute_commands_with_stm32(commands):
        """
        Execute STM32 commands with real hardware.
        
        - Movement commands (SF/SB/LF/RF): sent to STM32, wait for ACK
        - SNAP commands: skipped (printed only, no camera check)
        - FIN: prints completion
        
        Args:
            commands: List of STM32 command strings from Algo PC
        """
        nonlocal executing_commands
        executing_commands = True
        total = len(commands)
        
        print(f"\n{'='*60}")
        print(f"[STM] Starting movement execution: {total} commands")
        print(f"[STM] Commands: {commands}")
        print(f"{'='*60}\n")
        
        for i, cmd in enumerate(commands):
            if not running or not executing_commands:
                print("[STM] Execution stopped")
                break
            
            cmd = cmd.strip()
            
            # ---- FIN: Done ----
            if cmd == "FIN":
                print(f"\n[STM] [{i+1}/{total}] FIN - All obstacles visited!")
                if bt.is_connected():
                    bt.send("TARGET,DONE,FIN")
                    print("[RPi → BT] TARGET,DONE,FIN")
                break
            
            # ---- SNAP: Skip (no camera) ----
            if cmd.startswith("SNAP"):
                snap_body = cmd[4:]
                parts = snap_body.split("_")
                obstacle_id = parts[0]
                position = parts[1] if len(parts) > 1 else "C"
                
                print(f"\n[STM] [{i+1}/{total}] {cmd} → SKIPPED (no camera)")
                print(f"[STM] (Would detect obstacle {obstacle_id}, position {position})")
                
                # Notify BT that we skipped detection
                if bt.is_connected():
                    bt.send(f"TARGET,{obstacle_id},SKIPPED")
                    print(f"[RPi → BT] TARGET,{obstacle_id},SKIPPED")
                continue
            
            # ---- Movement commands: SF, SB, LF, RF, LB, RB ----
            if cmd.startswith(("SF", "SB", "LF", "RF", "LB", "RB")):
                cmd_type = cmd[:2]
                cmd_val = cmd[2:]
                
                labels = {
                    "SF": "FORWARD", 
                    "SB": "BACKWARD", 
                    "LF": "LEFT FORWARD TURN", 
                    "RF": "RIGHT FORWARD TURN",
                    "LB": "LEFT BACKWARD TURN",
                    "RB": "RIGHT BACKWARD TURN"
                }
                label = labels.get(cmd_type, cmd_type)
                
                if cmd_type in ("SF", "SB"):
                    print(f"[STM] [{i+1}/{total}] {cmd} → {label} {cmd_val}cm")
                else:
                    print(f"[STM] [{i+1}/{total}] {cmd} → {label} {cmd_val}°")
                
                # Send to real STM32
                if stm32_ok and stm.connected:
                    print(f"[STM] → STM32: {cmd}")
                    if stm.send(cmd):
                        response = stm.receive(timeout=STM32_ACK_TIMEOUT)
                        if response:
                            print(f"[STM] ← STM32 ACK: {response}")
                        else:
                            print(f"[STM] ⚠ STM32 no ACK for {cmd} (timeout {STM32_ACK_TIMEOUT}s)")
                    else:
                        print(f"[STM] ✗ Failed to send {cmd} to STM32")
                else:
                    print(f"[STM] ⚠ STM32 not connected - command not sent")
                continue
            
            # ---- Unknown command ----
            print(f"[STM] [{i+1}/{total}] Unknown command: {cmd}")
        
        executing_commands = False
        print(f"\n{'='*60}")
        print("[STM] Movement execution complete")
        print(f"{'='*60}")
        print(">> ", end='', flush=True)
    
    def receive_algopc_thread():
        """Receive from Algo PC, parse commands, execute with STM32"""
        while running:
            try:
                if not algo.is_connected():
                    time.sleep(0.5)
                    continue
                
                msg = algo.receive(timeout=0.1)
                if msg:
                    msg = msg.strip()
                    msg_count['algo'] += 1
                    print(f"\n[AlgoPC → RPi] {msg[:200]}{'...' if len(msg) > 200 else ''}")
                    
                    # Try to parse as JSON with commands
                    try:
                        data = json.loads(msg)
                        if isinstance(data, dict) and "commands" in data:
                            commands = data["commands"]
                            print(f"[Mode 7] Received {len(commands)} STM32 commands from Algo PC")
                            
                            # Forward command list to BT for visibility
                            if bt.is_connected():
                                bt.send(f"COMMANDS:{json.dumps(commands)}")
                            
                            # Guard: don't start a second executor while one is running
                            if executing_commands:
                                print("[Mode 7] WARNING: Already executing commands, ignoring new path")
                            else:
                                exec_thread = threading.Thread(
                                    target=execute_commands_with_stm32,
                                    args=(commands,),
                                    daemon=True
                                )
                                exec_thread.start()
                        elif isinstance(data, list):
                            if data and isinstance(data[0], str):
                                print(f"[Mode 7] Received {len(data)} commands (list format)")
                                if executing_commands:
                                    print("[Mode 7] WARNING: Already executing commands, ignoring new path")
                                else:
                                    exec_thread = threading.Thread(
                                        target=execute_commands_with_stm32,
                                        args=(data,),
                                        daemon=True
                                    )
                                    exec_thread.start()
                            else:
                                print("[Mode 7] Received raw path (legacy) - forwarding to BT")
                                if bt.is_connected():
                                    bt.send(msg)
                        else:
                            if bt.is_connected():
                                bt.send(msg)
                                print(f"[RPi → BT] {msg}")
                    except json.JSONDecodeError:
                        if bt.is_connected():
                            bt.send(msg)
                            print(f"[RPi → BT] {msg}")
                    
                    print(">> ", end='', flush=True)
                elif not algo.is_connected():
                    print("\n[DISCONNECTED] Algorithm PC disconnected")
                    print(">> ", end='', flush=True)
                    time.sleep(1)
            except Exception as e:
                if running and algo.is_connected():
                    print(f"\n[AlgoPC Error] {e}")
                    print(">> ", end='', flush=True)
                time.sleep(0.5)
    
    # Start all background threads
    algo_conn_thread = threading.Thread(target=algo_connection_thread, daemon=True)
    algo_conn_thread.start()
    
    bt_conn_thread = threading.Thread(target=bluetooth_connection_thread, daemon=True)
    bt_conn_thread.start()
    
    recv_bt_thread = threading.Thread(target=receive_bluetooth_thread, daemon=True)
    recv_bt_thread.start()
    
    recv_algo_thread = threading.Thread(target=receive_algopc_thread, daemon=True)
    recv_algo_thread.start()
    
    # Main command loop
    try:
        while running:
            cmd = input(">> ").strip()
            
            if cmd.lower() == 'q':
                break
            elif cmd.lower() == 'status':
                print(f"\n  Bluetooth  : {'Connected' if bt.is_connected() else 'Waiting...'}")
                print(f"  AlgoPC     : {'Connected' if algo.is_connected() else 'Waiting...'}")
                print(f"  STM32      : {'Connected (' + stm.port + ')' if stm32_ok and stm.connected else 'NOT CONNECTED'}")
                print(f"  Camera     : DISABLED (movement test)")
                print(f"  Executing  : {'Yes' if executing_commands else 'No'}")
                print(f"\n  Messages Received:")
                print(f"    BT → RPi    : {msg_count['bt']}")
                print(f"    AlgoPC → RPi: {msg_count['algo']}")
                print()
            elif cmd.lower().startswith('bt '):
                message = cmd[3:].strip()
                if bt.is_connected():
                    bt.send(message)
                    print(f"[RPi → BT] {message}")
                else:
                    print("[WARN] Bluetooth not connected")
            elif cmd.lower().startswith('algo '):
                message = cmd[5:].strip()
                if algo.is_connected():
                    algo.send(message)
                    print(f"[RPi → AlgoPC] {message}")
                else:
                    print("[WARN] Algo PC not connected")
            elif cmd.lower().startswith('stm '):
                stm_cmd = cmd[4:].strip().upper()
                if stm32_ok and stm.connected:
                    print(f"[Manual] → STM32: {stm_cmd}")
                    if stm.send(stm_cmd):
                        response = stm.receive(timeout=STM32_ACK_TIMEOUT)
                        if response:
                            print(f"[Manual] ← STM32 ACK: {response}")
                        else:
                            print(f"[Manual] No ACK (timeout)")
                    else:
                        print("[Manual] Failed to send")
                else:
                    print("[WARN] STM32 not connected")
            elif cmd:
                print("Unknown command. Use: status, bt <text>, algo <text>, stm <cmd>, q")
    
    except KeyboardInterrupt:
        print("\n\n[Mode 7] Interrupted by user")
    finally:
        running = False
        executing_commands = False
        bt.disconnect(keep_server=False)
        algo.disconnect(keep_server=False)
        stm.disconnect()
        print("\n[Mode 7] STM32 movement test ended")
        print(f"[Mode 7] Total messages: BT={msg_count['bt']}, Algo={msg_count['algo']}")


# =============================================================================
# Main Process Manager
# =============================================================================
class MultiProcessManager:
    def __init__(self, config: Config, task_num: int, mode: str = "hardcoded"):
        """
        Initialize process manager
        
        Args:
            config: Configuration object
            task_num: Task number (1 or 2)
            mode: "hardcoded" or "algorithm"
        """
        self.config = config
        self.task_num = task_num
        self.mode = mode
        self.processes = {}
        self.queues = {}
        self.stop_event = mp.Event()
        
    def setup(self):
        """Initialize queues and all processes"""
        # Create queues for inter-process communication
        self.queues = {
            'bt_to_algo': Queue(),      # Obstacle coords: BT → Algo
            'task_to_bt': Queue(),      # Image rec results: Task → BT
            'algo_to_task': Queue(),    # Path commands: Algo → Task
            'bt_to_task': Queue(),      # Commands: BT → Task (future)
            'algo_to_bt': Queue(),      # Commands: Algo → BT (for Android visibility)
        }
        
        # Create processes
        self.processes['bluetooth'] = Process(
            target=bluetooth_process,
            args=(
                self.queues['bt_to_algo'],
                self.queues['task_to_bt'],
                self.queues['bt_to_task'],
                self.queues['algo_to_bt'],
                self.stop_event,
                self.config
            ),
            name='BluetoothProcess'
        )
        
        self.processes['task'] = Process(
            target=task_process,
            args=(
                self.task_num,
                self.queues['task_to_bt'],
                self.queues['algo_to_task'],
                self.queues['bt_to_task'],
                self.stop_event,
                self.config,
                self.mode  # Pass mode to task process
            ),
            name='TaskProcess'
        )
        
        self.processes['algorithm'] = Process(
            target=algorithm_process,
            args=(
                self.queues['bt_to_algo'],
                self.queues['algo_to_task'],
                self.queues['algo_to_bt'],
                self.stop_event,
                self.config
            ),
            name='AlgorithmProcess'
        )
        
    def start(self):
        """Start all processes"""
        for name, proc in self.processes.items():
            proc.start()
            print(f"[Main] {name} process started (PID: {proc.pid})")
        
    def restart_process(self, name: str):
        """Restart a specific process"""
        if name in self.processes:
            proc = self.processes[name]
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=2.0)
            
            # Recreate process (processes can only be started once)
            if name == 'bluetooth':
                self.processes['bluetooth'] = Process(
                    target=bluetooth_process,
                    args=(
                        self.queues['bt_to_algo'],
                        self.queues['task_to_bt'],
                        self.queues['bt_to_task'],
                        self.stop_event,
                        self.config
                    ),
                    name='BluetoothProcess'
                )
            elif name == 'task':
                self.processes['task'] = Process(
                    target=task_process,
                    args=(
                        self.task_num,
                        self.queues['task_to_bt'],
                        self.queues['algo_to_task'],
                        self.queues['bt_to_task'],
                        self.stop_event,
                        self.config,
                        self.mode  # Pass mode to task process
                    ),
                    name='TaskProcess'
                )
            elif name == 'algorithm':
                self.processes['algorithm'] = Process(
                    target=algorithm_process,
                    args=(
                        self.queues['bt_to_algo'],
                        self.queues['algo_to_task'],
                        self.stop_event,
                        self.config
                    ),
                    name='AlgorithmProcess'
                )
            
            self.processes[name].start()
            print(f"[Main] {name} process restarted (PID: {self.processes[name].pid})")
        
    def stop(self):
        """Gracefully stop all processes"""
        print("[Main] Stopping all processes...")
        self.stop_event.set()
        
        for name, proc in self.processes.items():
            proc.join(timeout=3.0)
            if proc.is_alive():
                proc.terminate()
                print(f"[Main] {name} force terminated")
                
        print("[Main] All processes stopped")
        
    def status(self):
        """Print status of all processes"""
        for name, proc in self.processes.items():
            status = "running" if proc.is_alive() else "stopped"
            print(f"  {name}: {status} (PID: {proc.pid})")
        
    def run(self):
        """Main loop"""
        self.setup()
        self.start()
        
        print("\n" + "="*50)
        print("Commands:")
        print("  status   - show process status")
        print("  restart <bt|task|algo> - restart a process")
        print("  q        - quit")
        print("="*50 + "\n")
        
        try:
            while True:
                cmd = input(">> ").strip().lower()
                
                if cmd == 'q':
                    break
                elif cmd == 'status':
                    self.status()
                elif cmd.startswith('restart '):
                    proc_name = cmd.split()[1]
                    name_map = {'bt': 'bluetooth', 'task': 'task', 'algo': 'algorithm'}
                    if proc_name in name_map:
                        self.restart_process(name_map[proc_name])
                    else:
                        print("Unknown process. Use: bt, task, algo")
                elif cmd:
                    print("Unknown command")
                    
        except KeyboardInterrupt:
            print("\n[Main] Interrupted")
        finally:
            self.stop()


def select_run_mode() -> str:
    """Prompt user to select run mode"""
    print("\n" + "=" * 50)
    print("RPI_v3 - Select Run Mode")
    print("=" * 50)
    print("  1. Full Task Mode (BT + PC + Algorithm)")
    print("  2. Bluetooth Only Test (2-way communication)")
    print("  3. Bluetooth + STM32 Bridge Test (BT commands → STM32)")
    print("  4. Bluetooth + Algorithm PC Bridge (BT ↔ RPi ↔ AlgoPC)")
    print("  5. Image Rec PC Communication Test (RPi ↔ ImgRec PC)")
    print("  6. Full Integration Simulation (BT + Algo + ImgRec, no STM32)")
    print("  7. STM32 Movement Test (BT + Algo + STM32, no camera)")
    
    while True:
        mode = input("\nSelect mode (1-7) >> ").strip()
        if mode in ['1', '2', '3', '4', '5', '6', '7']:
            return mode
        print("Please enter 1-7")


def select_task() -> int:
    """Prompt user to select task"""
    while True:
        task_str = input("Enter task number (1 / 2) >> ")
        try:
            task_num = int(task_str)
            if task_num in [1, 2]:
                return task_num
            print("Please enter either 1 or 2.")
        except ValueError:
            print("Please enter a valid number.")


def select_mode() -> str:
    """Prompt user to select movement mode"""
    print("\nMovement mode:")
    print("  1. hardcoded - Use IMAGE_COMMANDS mapping (arrows trigger turns)")
    print("  2. algorithm - Wait for path commands from Algorithm")
    
    while True:
        mode_str = input("Enter mode (1=hardcoded / 2=algorithm) >> ").strip()
        if mode_str == "1" or mode_str.lower() == "hardcoded":
            return "hardcoded"
        elif mode_str == "2" or mode_str.lower() == "algorithm":
            return "algorithm"
        print("Please enter 1 or 2.")


if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)
    
    run_mode = select_run_mode()
    
    if run_mode == '1':
        # Full Task Mode
        task_num = select_task()
        config = get_config()
        mode = select_mode()
        
        print(f"\nStarting Task {task_num} in {mode} mode...")
        
        manager = MultiProcessManager(config, task_num, mode)
        manager.run()
        
    elif run_mode == '2':
        # Bluetooth Only Test
        run_bluetooth_test()
        
    elif run_mode == '3':
        # Bluetooth + STM32 Bridge Test
        run_bluetooth_stm32_test()
    
    elif run_mode == '4':
        # Bluetooth + Algorithm PC Bridge Test
        run_bluetooth_algo_bridge()
    
    elif run_mode == '5':
        # Image Rec PC Communication Test
        run_imgrec_pc_test()
    
    elif run_mode == '6':
        # Full Integration Simulation (BT + Algo + ImgRec, no STM32)
        run_full_integration_test()
    
    elif run_mode == '7':
        # STM32 Movement Test (BT + Algo + STM32, no camera)
        run_stm32_movement_test()

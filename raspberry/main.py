"""
RPi Multiprocessing Communication
=================================
Architecture:
- Bluetooth: Android tablet (control)
- WiFi TCP:  Algorithm PC (sends path once at start)
- WiFi TCP:  Detection PC (receives camera stream, sends detection results)
- UART:      STM32 (motor commands)
"""

import time
from multiprocessing import Process, Queue, Event


# ============== BLUETOOTH PROCESS (Android) ==============
def bluetooth_process(tx_queue: Queue, rx_queue: Queue):
    """Handle Bluetooth communication with Android."""
    print("[BT] Process started")
    
    while True:
        while not tx_queue.empty():
            msg = tx_queue.get_nowait()
            if msg == "SHUTDOWN":
                print("[BT] Shutting down")
                return
            print(f"[BT] Sending: {msg}")
            # TODO: Send via Bluetooth
        
        # TODO: Receive from Bluetooth
        # rx_queue.put({"source": "android", "data": received_data})
        
        time.sleep(0.01)


# ============== ALGORITHM WIFI PROCESS ==============
def algorithm_process(tx_queue: Queue, rx_queue: Queue):
    """Handle WiFi communication with Algorithm PC (path planning)."""
    print("[Algo] Process started - waiting for path from Algorithm PC")
    
    # Algorithm PC connects, sends path, then we're done with it
    while True:
        while not tx_queue.empty():
            msg = tx_queue.get_nowait()
            if msg == "SHUTDOWN":
                print("[Algo] Shutting down")
                return
            print(f"[Algo] Sending: {msg}")
            # TODO: Send via TCP (port 5000)
        
        # TODO: Receive path from Algorithm PC
        # rx_queue.put({"source": "algorithm", "data": path_commands})
        
        time.sleep(0.01)


# ============== DETECTION WIFI PROCESS ==============
def detection_process(tx_queue: Queue, rx_queue: Queue, stream_queue: Queue):
    """Handle WiFi communication with Detection PC (receives stream, sends results)."""
    print("[Detect] Process started - streaming to Detection PC")
    
    while True:
        while not tx_queue.empty():
            msg = tx_queue.get_nowait()
            if msg == "SHUTDOWN":
                print("[Detect] Shutting down")
                return
            print(f"[Detect] Sending: {msg}")
            # TODO: Send via TCP (port 5001)
        
        # Check for frames to stream
        while not stream_queue.empty():
            frame = stream_queue.get_nowait()
            # TODO: Send frame to Detection PC
            pass
        
        # TODO: Receive detection results
        # rx_queue.put({"source": "detection", "data": {"label": "A", "conf": 0.95}})
        
        time.sleep(0.01)


# ============== CAMERA PROCESS ==============
def camera_process(stream_queue: Queue, control_queue: Queue):
    """Capture frames and send to stream queue."""
    print("[Camera] Process started")
    
    # TODO: Initialize camera
    # from picamera2 import Picamera2
    # camera = Picamera2()
    # camera.start()
    
    streaming = True
    
    while True:
        # Check for control commands
        while not control_queue.empty():
            cmd = control_queue.get_nowait()
            if cmd == "SHUTDOWN":
                print("[Camera] Shutting down")
                return
            elif cmd == "START":
                streaming = True
                print("[Camera] Streaming started")
            elif cmd == "STOP":
                streaming = False
                print("[Camera] Streaming stopped")
        
        # Capture and queue frame
        if streaming:
            # TODO: Capture frame
            # frame = camera.capture_array()
            # stream_queue.put(frame)
            pass
        
        time.sleep(0.033)  # ~30 FPS


# ============== UART PROCESS (STM32) ==============
def uart_process(tx_queue: Queue, rx_queue: Queue):
    """Handle UART communication with STM32."""
    print("[UART] Process started")
    
    while True:
        while not tx_queue.empty():
            msg = tx_queue.get_nowait()
            if msg == "SHUTDOWN":
                print("[UART] Shutting down")
                return
            print(f"[UART] Sending: {msg}")
            # TODO: Send via serial
        
        # TODO: Receive ACK from STM32
        # rx_queue.put({"source": "stm32", "data": "ACK"})
        
        time.sleep(0.01)


# ============== MAIN ==============
def main():
    # Queues for each communication channel
    bt_tx, bt_rx = Queue(), Queue()           # Android
    algo_tx, algo_rx = Queue(), Queue()       # Algorithm PC
    detect_tx, detect_rx = Queue(), Queue()   # Detection PC
    uart_tx, uart_rx = Queue(), Queue()       # STM32
    
    # Camera queues
    stream_queue = Queue()    # Frames to stream
    camera_ctrl = Queue()     # Camera control (START/STOP)
    
    # Start all processes
    processes = [
        Process(target=bluetooth_process, args=(bt_tx, bt_rx), name="BT"),
        Process(target=algorithm_process, args=(algo_tx, algo_rx), name="Algo"),
        Process(target=detection_process, args=(detect_tx, detect_rx, stream_queue), name="Detect"),
        Process(target=camera_process, args=(stream_queue, camera_ctrl), name="Camera"),
        Process(target=uart_process, args=(uart_tx, uart_rx), name="UART"),
    ]
    
    for p in processes:
        p.daemon = True
        p.start()
    
    print("[Main] All 5 processes started")
    print("  - Bluetooth (Android)")
    print("  - Algorithm WiFi (path planning PC)")
    print("  - Detection WiFi (camera stream + detection PC)")
    print("  - Camera (frame capture)")
    print("  - UART (STM32)")
    
    # State
    path_commands = []      # Commands from Algorithm PC
    current_cmd_idx = 0     # Which command we're executing
    waiting_for_ack = False # Waiting for STM32 ACK
    
    try:
        while True:
            # ============== FROM ANDROID (Bluetooth) ==============
            while not bt_rx.empty():
                msg = bt_rx.get()
                print(f"[Main] From Android: {msg}")
                data = msg.get("data", {})
                
                # Check message type
                msg_type = data.get("type") if isinstance(data, dict) else data
                
                if msg_type == "START":
                    # Start executing path
                    if path_commands and not waiting_for_ack:
                        current_cmd_idx = 0
                        cmd = path_commands[current_cmd_idx]
                        uart_tx.put(cmd)
                        waiting_for_ack = True
                        print(f"[Main] Starting path, sent: {cmd}")
                
                elif msg_type == "OBSTACLES":
                    # Forward obstacle data to Algorithm PC
                    # Expected: {"type": "OBSTACLES", "obstacles": [...], "robot": {...}}
                    algo_tx.put(data)
                    print(f"[Main] Forwarded obstacles to Algorithm PC")
                
                elif msg_type == "RESET":
                    # Reset state
                    path_commands = []
                    current_cmd_idx = 0
                    waiting_for_ack = False
                    print(f"[Main] State reset")
            
            # ============== FROM ALGORITHM PC (path commands - once) ==============
            while not algo_rx.empty():
                msg = algo_rx.get()
                print(f"[Main] From Algorithm: {msg}")
                
                # Store path commands
                # Expected format: {"commands": ["SF030", "RF090", "SNAP", ...]}
                if "commands" in msg.get("data", {}):
                    path_commands = msg["data"]["commands"]
                    print(f"[Main] Received {len(path_commands)} path commands")
                    # Notify Android
                    bt_tx.put({"type": "PATH_RECEIVED", "count": len(path_commands)})
            
            # ============== FROM DETECTION PC (YOLO results) ==============
            while not detect_rx.empty():
                msg = detect_rx.get()
                print(f"[Main] From Detection: {msg}")
                
                # Detection result received
                # Expected: {"label": "A", "confidence": 0.95}
                detection = msg.get("data", {})
                label = detection.get("label")
                
                if label:
                    print(f"[Main] IMAGE DETECTED: {label}")
                    
                    # Send to Android for display
                    bt_tx.put({"type": "IMAGE_DETECTED", "label": label})
                    
                    # Send SNAP acknowledgment to STM32 (or next command)
                    # This signals detection complete, robot can continue
                    uart_tx.put("SNAPD")  # SNAP Done
                    print(f"[Main] Sent SNAPD to STM32 (detection: {label})")
            
            # ============== FROM STM32 (ACK) ==============
            while not uart_rx.empty():
                msg = uart_rx.get()
                print(f"[Main] From STM32: {msg}")
                
                if msg.get("data") == "ACK":
                    waiting_for_ack = False
                    current_cmd_idx += 1
                    
                    # Send next command if available
                    if current_cmd_idx < len(path_commands):
                        cmd = path_commands[current_cmd_idx]
                        
                        if cmd == "SNAP":
                            # Trigger camera to take photo for detection
                            detect_tx.put({"action": "DETECT"})
                            print(f"[Main] SNAP command - requesting detection")
                            # Wait for detection result before continuing
                        else:
                            # Movement command - send to STM32
                            uart_tx.put(cmd)
                            waiting_for_ack = True
                            print(f"[Main] Sent next command: {cmd}")
                    else:
                        print("[Main] Path complete!")
                        bt_tx.put({"type": "PATH_COMPLETE"})
            
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n[Main] Shutting down...")
    
    # Shutdown all
    for q in [bt_tx, algo_tx, detect_tx, camera_ctrl, uart_tx]:
        q.put("SHUTDOWN")
    
    for p in processes:
        p.join(timeout=2)


if __name__ == "__main__":
    main()

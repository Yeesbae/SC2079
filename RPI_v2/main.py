import multiprocessing as mp
from multiprocessing import Process, Queue, Event
import time
import sys

from config.config import get_config, Config


# =============================================================================
# Process 1: Bluetooth (Android Communication)
# =============================================================================
def bluetooth_process(
    to_algo_queue: Queue,      # Send obstacle coords to Algorithm
    from_task_queue: Queue,    # Receive image rec results from Task
    to_task_queue: Queue,      # Send commands to Task (future use)
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
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f"[BT Process] Error: {e}")
            bt.disconnect()
            time.sleep(1)
    
    # Cleanup
    bt.disconnect()
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
    
    Args:
        mode: "hardcoded" - use IMAGE_COMMANDS dict for movements
              "algorithm" - wait for path commands from Algorithm process
    """
    # Import here for multiprocessing spawn compatibility
    from tasks.task1_rpi import Task1RPI
    from tasks.task2_rpi import Task2RPI
    
    print(f"[Task Process] Starting Task {task_num} in {mode} mode...")
    
    if task_num == 1:
        task = Task1RPI(config, mode=mode)
    else:
        task = Task2RPI(config)
    
    task.initialize()
    
    try:
        while not stop_event.is_set():
            # Get last image and forward to Bluetooth process
            last_img = task.get_last_image()
            if last_img:
                to_bt_queue.put(f"IMG:{last_img}")
                task.last_image = None  # Clear after forwarding
            
            # Check for STM32 commands from Bluetooth
            if not from_bt_queue.empty():
                bt_msg = from_bt_queue.get_nowait()
                if isinstance(bt_msg, tuple) and bt_msg[0] == 'STM32':
                    stm32_cmd = bt_msg[1]
                    print(f"[Task Process] Executing STM32 command from BT: {stm32_cmd}")
                    if hasattr(task, 'send_command'):
                        response = task.send_command(stm32_cmd)
                        if response:
                            to_bt_queue.put(f"STM32:{response}")
            
            # Check for path commands from Algorithm
            if not from_algo_queue.empty():
                path_cmd = from_algo_queue.get_nowait()
                print(f"[Task Process] Received path: {path_cmd}")
                
                # Execute path if in algorithm mode
                if mode == "algorithm" and hasattr(task, 'execute_path'):
                    if isinstance(path_cmd, list):
                        task.execute_path(path_cmd)
                    elif isinstance(path_cmd, str):
                        import json
                        try:
                            path = json.loads(path_cmd)
                            task.execute_path(path)
                        except json.JSONDecodeError:
                            print(f"[Task Process] Invalid path format: {path_cmd}")
            
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
    to_task_queue: Queue,      # Send path to Task (future use)
    stop_event: Event,
    config: Config
):
    """
    Algorithm process - handles Algorithm PC communication
    """
    # Import here for multiprocessing spawn compatibility
    from communication.algo_pc import AlgoPC
    
    print("[Algo Process] Starting...")
    
    # Initialize Algorithm PC connection
    algo = AlgoPC()
    algo.connect()
    
    while not stop_event.is_set():
        try:
            # Receive obstacle coords from Bluetooth (from Android)
            if not from_bt_queue.empty():
                coords = from_bt_queue.get_nowait()
                print(f"[Algo Process] Received coords: {coords}")
                
                # Send coords to Algorithm PC (as JSON if dict, else string)
                if isinstance(coords, dict):
                    algo.send_json(coords)
                else:
                    algo.send(str(coords))
                
                # Receive path from Algorithm PC
                try:
                    path = algo.receive()
                    if path:
                        print(f"[Algo Process] Received path: {path}")
                        to_task_queue.put(path)
                except:
                    pass
            
            stop_event.wait(timeout=0.1)
            
        except Exception as e:
            print(f"[Algo Process] Error: {e}")
            time.sleep(1)
    
    # Cleanup
    algo.disconnect()
    print("[Algo Process] Stopped")


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
        }
        
        # Create processes
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
    
    task_num = select_task()
    config = get_config()
    mode = select_mode()
    
    print(f"\nStarting Task {task_num} in {mode} mode...")
    
    manager = MultiProcessManager(config, task_num, mode)
    manager.run()

"""
STM32 UART Communication Process
================================
Handles USB/UART communication with STM32F407VET microcontroller.

Protocol:
- Commands: 5-byte format (e.g., 'SF010' for forward 10cm)
- ACK: Single 'A' character from STM32
- All commands forwarded from main process via queue
"""

import serial
import serial.tools.list_ports
import time
from multiprocessing import Process, Queue
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[STM32] %(message)s')
logger = logging.getLogger('STM32')

# Default configuration
DEFAULT_PORT = '/dev/ttyUSB0'
DEFAULT_BAUD = 115200
TIMEOUT = 0.1


class STM32Process:
    """
    STM32 UART communication handler for multiprocessing.
    
    Runs as a separate process, communicates via queues:
    - tx_queue: Commands to send to STM32 (from main process)
    - rx_queue: Responses from STM32 (to main process)
    """
    
    def __init__(self, tx_queue: Queue, rx_queue: Queue, 
                 port: str = DEFAULT_PORT, baudrate: int = DEFAULT_BAUD):
        self.tx_queue = tx_queue
        self.rx_queue = rx_queue
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.running = False
        
    def connect(self) -> bool:
        """Connect to STM32 via USB serial."""
        try:
            # Try specified port first
            try:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=TIMEOUT)
                logger.info(f"Connected on {self.port}")
                return True
            except serial.SerialException:
                pass
            
            # Auto-detect USB serial devices
            for port_info in serial.tools.list_ports.comports():
                device = port_info.device
                if 'ttyUSB' in device or 'ttyACM' in device:
                    try:
                        self.ser = serial.Serial(device, self.baudrate, timeout=TIMEOUT)
                        logger.info(f"Auto-detected and connected on {device}")
                        return True
                    except serial.SerialException:
                        continue
            
            logger.warning("No STM32 device found")
            return False
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def send_command(self, cmd: str) -> bool:
        """Send command to STM32."""
        if not self.ser or not self.ser.is_open:
            logger.warning("Cannot send - not connected")
            return False
        
        try:
            self.ser.write(cmd.encode('utf-8'))
            logger.info(f"TX: {cmd}")
            return True
        except Exception as e:
            logger.error(f"TX error: {e}")
            return False
    
    def read_response(self) -> Optional[str]:
        """Read response from STM32."""
        if not self.ser or not self.ser.is_open:
            return None
        
        try:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                return data
        except Exception as e:
            logger.error(f"RX error: {e}")
        
        return None
    
    def run(self):
        """Main process loop."""
        logger.info("Starting STM32 communication process...")
        
        # Try to connect
        while not self.connect():
            logger.info("Retrying connection in 2 seconds...")
            time.sleep(2)
        
        self.running = True
        rx_buffer = ""
        
        while self.running:
            try:
                # Check for commands to send
                while not self.tx_queue.empty():
                    try:
                        cmd = self.tx_queue.get_nowait()
                        if cmd == 'SHUTDOWN':
                            self.running = False
                            break
                        self.send_command(cmd)
                    except Exception:
                        break
                
                # Read responses from STM32
                data = self.read_response()
                if data:
                    rx_buffer += data
                    
                    # Check for ACK ('A')
                    while 'A' in rx_buffer:
                        logger.info("RX: ACK")
                        self.rx_queue.put({'type': 'ACK', 'source': 'stm32'})
                        rx_buffer = rx_buffer.replace('A', '', 1)
                    
                    # Process complete lines for debug output
                    while '\n' in rx_buffer:
                        line, rx_buffer = rx_buffer.split('\n', 1)
                        if line.strip():
                            logger.info(f"RX: {line.strip()}")
                            self.rx_queue.put({
                                'type': 'DATA',
                                'source': 'stm32', 
                                'data': line.strip()
                            })
                
                time.sleep(0.01)  # Small delay to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Process error: {e}")
                time.sleep(0.1)
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        if self.ser:
            self.ser.close()
        logger.info("STM32 process stopped")


def start_stm32_process(tx_queue: Queue, rx_queue: Queue, 
                        port: str = DEFAULT_PORT, baudrate: int = DEFAULT_BAUD) -> Process:
    """
    Start STM32 communication as a separate process.
    
    Args:
        tx_queue: Queue for commands to send to STM32
        rx_queue: Queue for responses from STM32
        port: Serial port (default: /dev/ttyUSB0)
        baudrate: Baud rate (default: 115200)
        
    Returns:
        Process object
    """
    def _run():
        handler = STM32Process(tx_queue, rx_queue, port, baudrate)
        handler.run()
    
    process = Process(target=_run, name="STM32-Process", daemon=True)
    process.start()
    logger.info(f"Process started (PID: {process.pid})")
    return process


# For testing standalone
if __name__ == "__main__":
    tx_q = Queue()
    rx_q = Queue()
    
    print("Starting STM32 process (standalone test)...")
    proc = start_stm32_process(tx_q, rx_q)
    
    try:
        while True:
            # Check for responses
            while not rx_q.empty():
                msg = rx_q.get()
                print(f"Received: {msg}")
            
            # Read user input
            cmd = input("Enter command (5 chars, or 'q' to quit): ")
            if cmd.lower() == 'q':
                break
            if len(cmd) == 5:
                tx_q.put(cmd)
            else:
                print("Command must be 5 characters")
                
    except KeyboardInterrupt:
        pass
    
    tx_q.put('SHUTDOWN')
    proc.join(timeout=2)
    print("Done")

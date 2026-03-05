"""
PC-side main entry point
"""
import socket
from time import sleep

from config.config import get_config
from tasks.task1_pc import main as task1_main
from tasks.task2_pc import main as task2_main

task_dict = {
    1: task1_main,
    2: task2_main
}


def test_send_loop():
    """Mode 3: Constantly send test messages to RPi to verify TCP connection"""
    host = "192.168.8.1"
    port = 5000
    print(f"# ------------- Test Send Mode ---------------- #")
    print(f"Connecting to RPi at {host}:{port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print(f"Connected to RPi successfully!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
    
    count = 0
    try:
        while True:
            count += 1
            msg = f"TEST,{count},hello_from_pc"
            sock.send(msg.encode("utf-8"))
            print(f"[{count}] Sent: {msg}")
            sleep(2)
    except KeyboardInterrupt:
        print("\nStopping test send loop...")
    except Exception as e:
        print(f"Send failed: {e}")
    finally:
        sock.close()
        print("Socket closed.")


if __name__ == "__main__":
    # Select task
    task_num = None
    while task_num is None:
        task_num_str = input("Enter task number (1 / 2 / 3=test send) >> ")
        try:
            task_num = int(task_num_str)
            if task_num not in [1, 2, 3]:
                print("Please enter 1, 2, or 3.")
                task_num = None
                continue
        except:
            print("Please enter a valid number.")
    
    if task_num == 3:
        test_send_loop()
    else:
        # Get configuration
        config = get_config()
        # Run selected task
        task_dict[task_num](config)

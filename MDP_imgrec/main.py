"""
PC-side main entry point
"""
from config.config import get_config
from tasks.task1_pc import main as task1_main
from tasks.task2_pc import main as task2_main

task_dict = {
    1: task1_main,
    2: task2_main
}

if __name__ == "__main__":
    # Select task
    task_num = None
    while task_num is None:
        task_num_str = input("Enter task number (1 / 2) >> ")
        try:
            task_num = int(task_num_str)
            if task_num not in [1, 2]:
                print("Please enter either 1 or 2.")
                task_num = None
                continue
        except:
            print("Please enter a valid number.")
    
    # Get configuration
    config = get_config()
    
    # Run selected task
    task_dict[task_num](config)

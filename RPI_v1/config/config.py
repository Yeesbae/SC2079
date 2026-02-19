"""
Configuration module
Manages model weights paths and parameters for Task1 and Task2
"""
class Config():
    def __init__(self, task1_weights, task2_weights):
        self.is_outdoors = False
        self.conf_threshold = 0.65
        # ========== MODIFY: Change to your model file paths ==========
        self.task1_weights = task1_weights
        self.task2_weights = task2_weights
        # =============================================================

class IndoorsConfig(Config):
    def __init__(self):
        # ========== MODIFY: Change to your model file paths ==========
        Config.__init__(self, 'v12_task1.pt', 'v9_task2.pt')
        # =============================================================

class OutdoorsConfig(Config):
    def __init__(self):
        # ========== MODIFY: Change to your model file paths ==========
        Config.__init__(self, 'v14_task1_outdoor.pt', 'v14_task1_outdoor.pt')
        # =============================================================
        self.is_outdoors = True
        self.conf_threshold = 0.6

def get_config():
    """
    Get configuration, select indoor or outdoor config based on user input
    """
    is_outdoors = None
    while is_outdoors is None:
        is_outdoors_str = input("Are you outdoors? (y/n) >> ").lower()
        if is_outdoors_str in ['y', 'n']:
            is_outdoors = is_outdoors_str == 'y'
            continue
            
        print("Please enter a valid character.")
    
    return OutdoorsConfig() if is_outdoors else IndoorsConfig()


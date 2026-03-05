"""
Configuration module
Manages model weight paths and parameters for Task1 and Task2
"""
class Config():
    def __init__(self, task1_weights, task2_weights):
        self.is_outdoors = False
        self.conf_threshold = 0.65
        # ========== Modify as needed: set your model file paths ==========
        self.task1_weights = task1_weights
        self.task2_weights = task2_weights
        # ================================================

class IndoorsConfig(Config):
    def __init__(self):
        # ========== Modify as needed: set your model file paths ==========
        Config.__init__(
            self,
            r'C:\Users\kaiyi\OneDrive\Desktop\SC2079\MDP_imgrec\models\best.pt',
            r'C:\Users\kaiyi\OneDrive\Desktop\SC2079\MDP_imgrec\models\best.pt',
        )
        # ================================================

class OutdoorsConfig(Config):
    def __init__(self):
        # ========== Modify as needed: set your model file paths ==========
        Config.__init__(
            self,
            r'C:\Users\kaiyi\OneDrive\Desktop\SC2079\MDP_imgrec\models\best.pt',
            r'C:\Users\kaiyi\OneDrive\Desktop\SC2079\MDP_imgrec\models\best.pt',
        )
        # ================================================
        self.is_outdoors = True
        self.conf_threshold = 0.6

def get_config():
    """
    Get configuration; select indoor or outdoor config based on user input
    """
    is_outdoors = None
    while is_outdoors is None:
        is_outdoors_str = input("Are you outdoors? (y/n) >> ").lower()
        if is_outdoors_str in ['y', 'n']:
            is_outdoors = is_outdoors_str == 'y'
            continue
            
        print("Please enter a valid character.")
    
    return OutdoorsConfig() if is_outdoors else IndoorsConfig()

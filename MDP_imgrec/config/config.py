"""
配置模块
管理Task1和Task2的模型权重路径和参数
"""
class Config():
    def __init__(self, task1_weights, task2_weights):
        self.is_outdoors = False
        self.conf_threshold = 0.65
        # ========== 需要修改：改为你的模型文件路径 ==========
        self.task1_weights = task1_weights
        self.task2_weights = task2_weights
        # ================================================

class IndoorsConfig(Config):
    def __init__(self):
        # ========== 需要修改：改为你的模型文件路径 ==========
        Config.__init__(
            self,
            r'C:\Users\huang\Desktop\MDP_imgrec\models\V5.pt',
            r'C:\Users\huang\Desktop\MDP_imgrec\models\V5.pt',
        )
        # ================================================

class OutdoorsConfig(Config):
    def __init__(self):
        # ========== 需要修改：改为你的模型文件路径 ==========
        Config.__init__(
            self,
            r'C:\Users\huang\Desktop\MDP_imgrec\models\V5.pt',
            r'C:\Users\huang\Desktop\MDP_imgrec\models\V5.pt',
        )
        # ================================================
        self.is_outdoors = True
        self.conf_threshold = 0.6

def get_config():
    """
    获取配置，根据用户输入选择室内或室外配置
    """
    is_outdoors = None
    while is_outdoors is None:
        is_outdoors_str = input("Are you outdoors? (y/n) >> ").lower()
        if is_outdoors_str in ['y', 'n']:
            is_outdoors = is_outdoors_str == 'y'
            continue
            
        print("Please enter a valid character.")
    
    return OutdoorsConfig() if is_outdoors else IndoorsConfig()


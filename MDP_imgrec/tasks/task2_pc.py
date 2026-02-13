"""
Task 2 PC端代码
负责接收视频流、进行YOLO识别、发送结果回RPi
"""
import socket
import sys
import threading
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera.stream_listener import StreamListener
from communication.pc_client import PCClient
from stitching.stitching import stitch_images, add_to_stitching_dict
from config.config import Config


class Task2PC:
    def __init__(self, config: Config):
        self.config = config
        
        self.exit = False
        self.pc_receive_thread = None
        self.stream_thread = None

        # ========== 需要修改：改为你的RPi IP地址 ==========
        self.host = "192.168.8.1"
        # ================================================
        self.port = 5000
        self.pc_client = None
        
        print(f"! -- initialising weights file: {config.task2_weights}....")
        self.stream_listener = StreamListener(config.task2_weights)

        # Task2特定的变量
        self.stitching_arr = []
        self.stitching_dict = {}
        self.filename = "task2"  # ========== 拼接文件的前缀名 ==========

        self.obstacle_id = 1
        self.obstacle_img_id = None

        # ========== 需要修改：根据你的模型调整左右箭头ID ==========
        self.LEFT_ARROW_ID = "39"
        self.RIGHT_ARROW_ID = "38"
        # =====================================================

    def start(self):
        """启动所有线程"""
        self.pc_client = PCClient(self.host, self.port)
        self.pc_client.connect()
        
        self.pc_receive_thread = threading.Thread(target=self.pc_receive)
        self.stream_thread = threading.Thread(target=self.stream_start)
        self.pc_receive_thread.start()  # 接收RPi指令
        self.stream_thread.start()  # 启动视频流识别

    def stream_start(self):
        """启动视频流识别"""
        self.stream_listener.start_stream_read(
            self.on_result, 
            self.on_disconnect, 
            conf_threshold=0.65,  # ========== 可根据需要调整置信度阈值 ==========
            show_video=True  # ========== 显示视频窗口和识别结果 ==========
        )

    def on_result(self, result, frame):
        """
        识别结果回调函数
        
        Args:
            result: YOLO识别结果
            frame: 图像帧
        """
        message_content = None

        if result is not None:
            conf_level = result.boxes[0].conf.item()
            img_id = result.names[int(result.boxes[0].cls[0].item())]

            # 只处理左右箭头
            if img_id not in [self.LEFT_ARROW_ID, self.RIGHT_ARROW_ID]:
                print(f"Detected invalid image {img_id}, skipping...")
                return
            
            if self.obstacle_img_id is None:
                # 首次检测到箭头，发送结果
                message_content = f"{conf_level},{img_id}"
                self.obstacle_img_id = img_id
            
            # 添加到拼接字典
            if img_id == self.obstacle_img_id:
                add_to_stitching_dict(
                    self.stitching_dict, 
                    self.obstacle_id, 
                    conf_level, 
                    frame
                )

        if message_content is not None:
            print("Sending:", message_content)
            self.pc_client.send(message_content)

    def on_disconnect(self):
        """视频流断开回调"""
        print("Stream disconnected, disconnect.")
        self.disconnect()

    def disconnect(self):
        """断开连接"""
        try:
            self.exit = True
            if self.pc_client:
                self.pc_client.disconnect()
            print("Disconnected from RPi successfully")
        except Exception as e:
            print(f"Failed to disconnect from RPi: {e}")

    def pc_receive(self) -> None:
        """
        接收RPi发送的指令
        
        接收的指令格式：
        1. "SEEN" - 表示已经看到箭头，准备检测下一个
        2. "STITCH" - 请求拼接图像
        """
        print("PC Socket connection started successfully")
        while not self.exit:
            try:
                message_rcv = self.pc_client.receive()
                if not message_rcv:
                    print("RPi connection dropped")
                    break
                print("Message received from RPi:", message_rcv)

                if "SEEN" in message_rcv:
                    # 指令: "SEEN" - 已看到箭头，准备下一个
                    self.obstacle_id += 1
                    self.obstacle_img_id = None
                    print(f"Obstacle ID incremented to {self.obstacle_id}")

                elif "STITCH" in message_rcv:
                    # 指令: "STITCH" - 开始拼接
                    # ========== 注意：这里假设拼接obstacle_id 1和2 ==========
                    stitch_images(
                        [1, 2], 
                        self.stitching_dict, 
                        filename=self.filename
                    )
                    # =====================================================
            except OSError as e:
                print("Error in receiving data:", e)
                break


def main(config: Config):
    """
    Task2主函数
    """
    print("# ------------- Running Task 2, PC ---------------- #")
    print(f"You are {'out' if config.is_outdoors else 'in'}doors.")
    pcMain = Task2PC(config)
    pcMain.start()
    
    # 保持运行
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        pcMain.disconnect()


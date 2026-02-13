"""
Task 1 PC端代码
负责接收视频流、进行YOLO识别、发送结果回RPi
"""
import socket
import sys
import threading
from pathlib import Path
from time import time_ns, sleep

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera.stream_listener import StreamListener
from communication.pc_client import PCClient
from stitching.stitching import stitch_images, add_to_stitching_dict
from config.config import Config


class Task1PC:
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

        print(f"! -- initialising weights file: {config.task1_weights}....")
        self.stream_listener = StreamListener(config.task1_weights)
        
        # Task1特定的变量
        self.IMG_BLACKLIST = ["marker"]  # ========== 可根据需要修改黑名单 ==========
        self.prev_image = None
        self.img_time_dict = {}  # 存储图像ID的时间戳
        self.time_advance_ns = 0.75e9  # ========== 时间匹配参数，可根据需要调整 ==========
        self.time_threshold_ns = 1.5e9
        self.img_pending_arr = []  # 待匹配的障碍物ID列表
        self.stitching_img_dict = {}  # 存储用于拼接的图像
        self.stitching_arr = []  # 要拼接的图像ID数组
        self.should_stitch = False
        self.stitch_len = 0  # 需要拼接的图像数量

        self.filename = "task1"  # ========== 拼接文件的前缀名 ==========
        self.start_time = time_ns()

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
            conf_threshold=self.config.conf_threshold, 
            show_video=True  # ========== 显示视频窗口和识别结果 ==========
        )
        
    def on_result(self, result, frame):
        """
        识别结果回调函数
        
        Args:
            result: YOLO识别结果
            frame: 图像帧
        """
        if result is not None:
            names = result.names
            
            for box in result.boxes:
                detected_img_id = names[int(box.cls[0].item())]
                detected_conf_level = box.conf.item()
                
                # 跳过黑名单中的图像
                if detected_img_id in self.IMG_BLACKLIST:
                    continue
                
                self.prev_image = detected_img_id
                # 添加到拼接字典
                add_to_stitching_dict(
                    self.stitching_img_dict, 
                    detected_img_id, 
                    detected_conf_level, 
                    frame
                )
                
                # 保存时间戳
                cur_time = time_ns()
                old_time = cur_time
                if detected_img_id in self.img_time_dict:
                    old_time = self.img_time_dict[detected_img_id][0]
                
                self.img_time_dict[detected_img_id] = (old_time, cur_time)
                
                # 检查是否有待匹配的障碍物
                rem = len(self.img_pending_arr)
                if rem > 0:
                    max_overlap = 0
                    max_obstacle_id = None
                    max_index = None
                    for i, (obstacle_id, timestamp) in enumerate(self.img_pending_arr):
                        overlap = self.check_timestamp(
                            detected_img_id, timestamp, old_time, cur_time
                        )
                        if overlap > max_overlap:
                            max_overlap = overlap
                            max_obstacle_id = obstacle_id
                            max_index = i

                    if max_obstacle_id is not None:
                        self.match_image(max_obstacle_id, detected_img_id)
                        self.img_pending_arr.pop(max_index)

                        # 如果所有图像都已找到，开始拼接
                        if self.should_stitch and len(self.stitching_arr) >= self.stitch_len:
                            print("Found last image, stitching now...")
                            self.stream_listener.close()
                            self.should_stitch = False
                            stitch_images(
                                self.stitching_arr, 
                                self.stitching_img_dict, 
                                filename=self.filename
                            )

        elif self.prev_image != "NONE":
            # 没有检测到对象
            self.prev_image = "NONE"

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

    def interval_overlap(self, int1, int2):
        """计算两个时间区间的重叠部分"""
        min1, max1 = int1
        min2, max2 = int2
        return min(max1, max2) - max(min1, min2)

    def check_timestamp(self, img_id, timestamp, old_time, cur_time):
        """
        检查图像ID的时间戳是否与障碍物时间戳匹配
        
        Args:
            img_id: 图像ID
            timestamp: 障碍物检测时间戳
            old_time: 图像首次检测时间
            cur_time: 图像当前检测时间
        """
        if img_id in self.stitching_arr:
            return 0
        
        timestamp_int = (
            timestamp - self.time_advance_ns, 
            timestamp + self.time_threshold_ns
        )
        comp_int = (old_time, cur_time)
        overlap = self.interval_overlap(comp_int, timestamp_int)
        return overlap
    
    def match_image(self, obstacle_id, img_id):
        """
        匹配障碍物ID和图像ID，发送结果到RPi
        
        Args:
            obstacle_id: 障碍物ID
            img_id: 图像ID
        """
        print(f"Matched obstacle ID {obstacle_id} as image ID {img_id}.")
        self.stitching_arr.append(img_id)
        print(f"Images found for stitching: {len(self.stitching_arr)}")
        
        # 发送格式: "obstacle_id,confidence,image_id"
        message_content = f"{obstacle_id},{self.stitching_img_dict[img_id][0]},{img_id}"
        print("Sending:", message_content)
        self.pc_client.send(message_content)

    def pc_receive(self) -> None:
        """
        接收RPi发送的指令
        
        接收的指令格式：
        1. "DETECT,obstacle_id" - 请求检测指定障碍物的图像
        2. "PERFORM STITCHING,num" - 请求拼接num个图像
        """
        print("PC Socket connection started successfully")
        while not self.exit:
            try:
                message_rcv = self.pc_client.receive()
                print("Message received from RPi:", message_rcv)

                if "DETECT" in message_rcv:
                    # 指令格式: "DETECT,obstacle_id"
                    obstacle_id = message_rcv.split(",")[1]
                    timestamp = time_ns()
                    
                    # 在时间戳字典中查找匹配的图像
                    max_overlap = 0
                    max_img_id = None
                    for img_id, (old_time, cur_time) in self.img_time_dict.items():
                        overlap = self.check_timestamp(img_id, timestamp, old_time, cur_time)
                        print(f"overlap: {overlap}, max overlap: {max_overlap}")
                        if overlap > 0 and overlap >= max_overlap:
                            print(f"replacing max overlap with {overlap}")
                            max_overlap = overlap
                            max_img_id = img_id
                    
                    if max_img_id is not None:
                        # 找到匹配的图像，立即发送
                        self.match_image(obstacle_id, max_img_id)
                        del self.img_time_dict[max_img_id]
                    else:
                        # 没有找到匹配的图像，加入待匹配列表
                        self.img_pending_arr.append((obstacle_id, timestamp))

                elif "PERFORM STITCHING" in message_rcv:
                    # 指令格式: "PERFORM STITCHING,num"
                    self.stitch_len = int(message_rcv.split(",")[1])
                    
                    if len(self.stitching_arr) < self.stitch_len:
                        # 图像还未全部找到，等待
                        print("Stitch request received, wait for completion...")
                        self.should_stitch = True
                        sleep(self.time_threshold_ns * 2e-9)
                        if self.should_stitch:
                            # 超时后仍没有全部找到，直接拼接已有的
                            stitch_images(
                                self.stitching_arr, 
                                self.stitching_img_dict, 
                                filename=self.filename
                            )
                    else:
                        # 所有图像都已找到，立即拼接
                        print("All images present, stitching now...")
                        self.stream_listener.close()
                        stitch_images(
                            self.stitching_arr, 
                            self.stitching_img_dict, 
                            filename=self.filename
                        )

                if not message_rcv:
                    print("RPi connection dropped")
                    break
            except OSError as e:
                print("Error in receiving data:", e)
                break


def main(config: Config):
    """
    Task1主函数
    """
    print("# ------------- Running Task 1, PC ---------------- #")
    print(f"You are {'out' if config.is_outdoors else 'in'}doors.")
    pcMain = Task1PC(config)
    pcMain.start()
    
    # 保持运行
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        pcMain.disconnect()


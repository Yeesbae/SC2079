import base64
import socket

import cv2
import numpy as np
from ultralytics import YOLO


class StreamListener:
    """
    UDP视频流客户端 + YOLO图像识别
    用于接收RPi发送的视频流并进行实时识别
    """
    def define_constants(self):
        self.BUFF_SIZE = 65536
        # ========== 需要修改：改为你的RPi IP地址 ==========
        self.HOST_ADDR = ("192.168.8.1", 5005)
        # ================================================
        self.REQ_STREAM = b"stream_request"

    def __init__(self, weights):
        """
        初始化StreamListener
        
        Args:
            weights: YOLO模型权重文件路径
        """
        # define constants.
        self.define_constants()

        # initialise model.
        # ========== 需要修改：确保weights路径正确 ==========
        self.model = YOLO(weights)
        # ================================================

        # intialise socket.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)

        # timeout of 3 seconds to signal disconnect.
        self.sock.settimeout(3)

    def req_stream(self):
        """发送流请求到RPi"""
        print("Sending request to HOST.")
        self.sock.sendto(self.REQ_STREAM, self.HOST_ADDR)

    def start_stream_read(
        self, on_result, on_disconnect, conf_threshold=0.7, show_video=True
    ):
        """
        开始接收视频流并进行识别
        
        Args:
            on_result: 回调函数，当检测到结果时调用 on_result(result, frame)
            on_disconnect: 回调函数，当连接断开时调用
            conf_threshold: 置信度阈值
            show_video: 是否显示视频窗口
        """
        # request for stream to be sent to this client.
        self.req_stream()
        
        # 跟踪GUI是否可用（macOS上可能失败）
        gui_available = show_video

        while True:
            packet = None
            try:
                packet, _ = self.sock.recvfrom(self.BUFF_SIZE)
            except:
                print("Timeout, ending stream")
                break

            # decode received packet and run prediction model.
            frame = base64.b64decode(packet)
            npdata = np.frombuffer(frame, dtype=np.uint8)
            frame = cv2.imdecode(npdata, cv2.IMREAD_COLOR)
            if frame is None:
                continue
            # RPi 端多为 RGB 输出，OpenCV 使用 BGR；若出现红/蓝互换（如棕色变蓝）则做此转换
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # ========== YOLO推理 ==========
            res = self.model.predict(
                frame,
                save=False,
                imgsz=frame.shape[1],
                conf=conf_threshold,
                verbose=False,
            )[0]
            # ==============================

            # perform actions based on results.
            annotated_frame = frame
            if len(res.boxes) > 0:
                annotated_frame = res.plot()
                on_result(res, annotated_frame)
            else:
                on_result(None, frame)

            if gui_available:
                try:
                    cv2.imshow("Stream", annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        break
                except (cv2.error, Exception) as e:
                    # macOS上GUI可能失败，继续运行但不显示视频
                    print(f"Warning: Cannot display video window ({type(e).__name__}: {e}).")
                    print("Continuing without video display. Recognition will still work normally.")
                    gui_available = False

        # call final disconnect handler.
        on_disconnect()

    def close(self):
        """释放资源并关闭"""
        self.sock.close()


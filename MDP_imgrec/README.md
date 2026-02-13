# PC端代码说明

## 文件结构

```
MDP_imgrec/
├── camera/                  # 摄像头相关模块
│   ├── __init__.py
│   └── stream_listener.py   # UDP视频流客户端 + YOLO识别
├── communication/           # 通信模块
│   ├── __init__.py
│   └── pc_client.py         # TCP客户端（发送消息到RPi）
├── config/                  # 配置模块
│   ├── __init__.py
│   └── config.py            # 配置类（模型路径、参数等）
├── stitching/               # 图像拼接模块
│   ├── __init__.py
│   └── stitching.py        # 拼接函数
├── tasks/                   # 任务相关代码
│   ├── __init__.py
│   ├── task1_pc.py         # Task 1 识别逻辑
│   └── task2_pc.py         # Task 2 识别逻辑
├── main.py                  # 入口文件
└── requirements.txt         # Python依赖
```

## 需要修改的部分

### 1. IP地址配置

**文件：`camera/stream_listener.py`**
```python
# 第15行
self.HOST_ADDR = ("192.168.14.14", 5005)  # 改为你的RPi IP地址
```

**文件：`communication/pc_client.py`**
```python
# 第20行（默认参数）
def __init__(self, host="192.168.14.14", port=5000):  # 改为你的RPi IP地址
```

**文件：`tasks/task1_pc.py`**
```python
# 第30行
self.host = "192.168.14.14"  # 改为你的RPi IP地址
```

**文件：`tasks/task2_pc.py`**
```python
# 第30行
self.host = "192.168.14.14"  # 改为你的RPi IP地址
```

### 2. 模型文件路径

**文件：`config/config.py`**
```python
# 第14行和第20行
Config.__init__(self, 'v12_task1.pt', 'v9_task2.pt')  # 改为你的模型文件路径
```

确保模型文件在PC端可以访问到。

### 3. Task1特定配置

**文件：`tasks/task1_pc.py`**
```python
# 第35行 - 黑名单（不需要识别的图像ID）
self.IMG_BLACKLIST = ["marker"]  # 可根据需要修改

# 第38-39行 - 时间匹配参数
self.time_advance_ns = 0.75e9    # 可根据需要调整
self.time_threshold_ns = 1.5e9

# 第45行 - 拼接文件前缀
self.filename = "task1"  # 可根据需要修改
```

### 4. Task2特定配置

**文件：`tasks/task2_pc.py`**
```python
# 第40-41行 - 左右箭头ID（根据你的模型调整）
self.LEFT_ARROW_ID = "39"
self.RIGHT_ARROW_ID = "38"

# 第35行 - 拼接文件前缀
self.filename = "task2"  # 可根据需要修改

# 第50行 - 置信度阈值
conf_threshold=0.65  # 可根据需要调整
```

## 安装依赖

```bash
pip install -r requirements.txt
```

**注意：** 安装 `torch` 和 `torchvision` 可能需要较长时间，建议使用GPU版本的PyTorch以加速推理。

## 运行方式

```bash
python main.py
```

然后按提示：
1. 选择任务编号（1 或 2，必须与RPi端一致）
2. 选择室内/室外（y/n，必须与RPi端一致）

## 视频显示功能

程序运行时会自动弹出视频窗口，实时显示：
- **接收到的视频帧**：从RPi传输过来的实时视频流
- **识别结果可视化**：YOLO检测框、标签和置信度会直接标注在视频上

### 使用方法
- **查看视频和识别结果**：程序启动后会自动打开名为 "Stream" 的视频窗口
- **退出视频窗口**：在视频窗口激活状态下，按 `q` 键退出（会断开连接）

### 关闭视频显示
如果不需要显示视频窗口（节省资源），可以修改以下文件：

**文件：`tasks/task1_pc.py`**
```python
# 第68行
show_video=False  # 改为 False 关闭视频显示
```

**文件：`tasks/task2_pc.py`**
```python
# 第65行
show_video=False  # 改为 False 关闭视频显示
```

## 功能说明

### Task 1
- 连接RPi的UDP视频流（端口5005）
- 使用YOLO模型进行实时图像识别
- 发送识别结果到RPi：`"obstacle_id,confidence,image_id"`
- 接收RPi指令：
  - `"DETECT,obstacle_id"` - 匹配指定障碍物的图像
  - `"PERFORM STITCHING,num"` - 拼接num个图像

### Task 2
- 连接RPi的UDP视频流（端口5005）
- 使用YOLO模型进行实时图像识别（只识别左右箭头）
- 发送识别结果到RPi：`"confidence,image_id"`
- 接收RPi指令：
  - `"SEEN"` - 已看到箭头，准备下一个
  - `"STITCH"` - 拼接图像

## 注意事项

1. **确保PC和RPi在同一网络**
2. **确保防火墙允许UDP 5005和TCP 5000端口**
3. **先启动RPi端，再启动PC端**
4. **Task1和Task2必须使用相同的任务编号和室内/室外配置**
5. **模型文件路径要正确，确保PC可以访问**
6. **如果使用GPU，确保CUDA已正确安装**
7. **macOS视频显示问题**：在macOS上，如果视频窗口无法显示（出现OpenCV错误），程序会自动继续运行但不显示视频。识别功能仍然正常工作。这是macOS上OpenCV GUI的已知限制。

## 输出文件

拼接后的图像会保存在当前目录，文件名格式：
- Task1: `task1_collage_HHMMSS.jpg`
- Task2: `task2_collage_HHMMSS.jpg`


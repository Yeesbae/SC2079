# RPI_v3 - Bluetooth Communication Test Version

This version is based on RPI_v2 with added **Bluetooth communication testing** capabilities.

## What's New in v3

- **Bluetooth Test Mode**: Dedicated mode to test 2-way Bluetooth communication
- **Interactive Tester**: Send/receive messages manually with Android
- **Automated Tester**: Auto-send periodic messages and echo received messages
- **Fixed AlgoPC timeout**: `receive()` now has timeout to prevent blocking

## File Structure

```
RPI_v3/
├── camera/
│   ├── __init__.py
│   └── stream_server.py      # UDP video stream server
├── communication/
│   ├── __init__.py
│   ├── algo_pc.py            # Algorithm PC TCP client (with timeout fix)
│   ├── bluetooth.py          # Bluetooth RFCOMM handler
│   ├── pc.py                 # Image Rec PC TCP server
│   └── stm32.py              # STM32 serial communication
├── config/
│   ├── __init__.py
│   └── config.py             # Configuration settings
├── tasks/
│   ├── __init__.py
│   ├── task1_rpi.py          # Task 1 implementation
│   └── task2_rpi.py          # Task 2 implementation
├── main.py                   # Main entry point with mode selection
├── test_bluetooth.py         # Standalone Bluetooth tester
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Quick Start

### 1. Install Dependencies

```bash
# System packages (Debian Bookworm)
sudo apt update
sudo apt install python3-libcamera python3-picamera2 python3-bluez bluetooth bluez

# Python packages
pip install -r requirements.txt
```

### 2. Setup Bluetooth

```bash
# Check Bluetooth status
sudo systemctl status bluetooth

# Make RPi discoverable
bluetoothctl
  > power on
  > discoverable on
  > pairable on
  > agent on
  > default-agent

# After Android pairs, trust it:
  > trust <ANDROID_MAC_ADDRESS>
  > quit
```

### 3. Run the Application

```bash
python main.py
```

You'll see:

```
RPI_v3 - Select Run Mode
==================================================
  1. Full Task Mode (BT + PC + Algorithm)
  2. Bluetooth Only Test (2-way communication)
  3. Run test_bluetooth.py (alternative tester)

Select mode (1/2/3) >>
```

## Testing Bluetooth Communication

### Option 1: Built-in Test (Mode 2)

```bash
python main.py
# Select option 2
```

Commands:
- Type any message → sends to Android
- `status` → shows connection status  
- `q` → quit

### Option 2: Standalone Tester

```bash
python test_bluetooth.py
```

Modes:
1. **Interactive**: Manual send/receive
2. **Automated**: Periodic test messages + auto-echo

## Communication Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                         RPi Processes                            │
├──────────────────┬───────────────────┬───────────────────────────┤
│   Bluetooth      │     Task          │     Algorithm             │
│   Process        │     Process       │     Process               │
│                  │                   │                           │
│ • Android ↔ RPi  │ • PC (port 5000)  │ • AlgoPC (port 6000)     │
│   (RFCOMM)       │ • Camera stream   │                           │
│                  │   (port 5005)     │                           │
│                  │ • STM32 (serial)  │                           │
└────────┬─────────┴────────┬──────────┴───────────────┬───────────┘
         │                  │                          │
         └──────────────────┴──────────────────────────┘
                     Multiprocessing Queues
```

## Key Fixes in v3

### 1. AlgoPC Timeout

```python
# OLD (blocks indefinitely)
def receive(self):
    data = self.socket.recv(4096)

# NEW (with timeout)
def receive(self, timeout=5.0):
    self.socket.settimeout(timeout)
    data = self.socket.recv(4096)
```

### 2. Bluetooth Non-blocking Receive

The Bluetooth handler uses `receive_nonblocking()` with configurable timeout to prevent blocking other processes.

## Troubleshooting

### Bluetooth Issues

```bash
# Release stuck RFCOMM ports
sudo rfcomm release all

# Restart Bluetooth service
sudo systemctl restart bluetooth

# Check if Bluetooth is blocked
rfkill list
rfkill unblock bluetooth
```

### Permission Issues

```bash
# Add user to bluetooth group
sudo usermod -a -G bluetooth $USER
# Logout and login again
```

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :5000
sudo lsof -i :5005

# Kill if needed
sudo kill <PID>
```

# 🚗 Real-Time Robot Control Dashboard (Android)

An Android-based control system for real-time robot navigation, featuring a car dashboard-style interface.

![Demo](android\sc2079_ay2526s2_grp08\assets\demo.gif)

---
# Android Control Dashboard

This module implements the Android application used to control and monitor the robot in real time.

The app acts as the UI and coordination layer between the user and the robot system, handling:

- Bluetooth communication
- arena rendering
- obstacle placement and editing
- robot playback visualization
- image detection display
- run timer and logs

---

## Core Rules

- UI only interacts with the backend through `MainViewModel`
- UI must **not** call `BluetoothManager` directly
- UI must **not** manually build or parse protocol strings
- Rendering is driven by `StateFlow<AppState>`

---

## Main Responsibilities

### 1. Bluetooth Communication
The app supports:

- server mode listening
- connecting to paired/discovered devices
- scanning and listing devices
- sending commands
- receiving status, path commands, detections, and images

Main ViewModel methods:

```kotlin
vm.startDefaultListening()
vm.disconnectAndReturnToListening()
vm.refreshPairedDevices()
vm.startScan()
vm.stopScan()
vm.connectToDevice(device)
vm.getDiscoverableIntent(300)
vm.isBluetoothSupported()
vm.isBluetoothEnabled()
```

UI reads:

- `state.conn`
- `state.pairedDevices`
- `state.scannedDevices`
- `state.isScanning`
- `state.log`

---

### 2. Arena and Robot Rendering
The arena screen visualizes:

- grid map
- robot position and facing
- placed obstacles
- obstacle target IDs after detection
- playback path trail
- drag/drop preview overlays

UI reads:

- `state.arena`
- `state.robot`
- `state.placedObstacles`
- `state.obstacleImages`
- `state.playbackPath`
- `state.pendingPreview`
- `state.dragPreview`

---

### 3. Obstacle Placement and Editing
Obstacles can be:

- selected by fixed ID
- placed directly by coordinates
- dragged on the arena
- edited through the obstacle details dialog
- assigned a facing direction
- reset back to their original state after image detection

Main ViewModel methods:

```kotlin
vm.pickObstacleToConfigure(obstacleId)
vm.updatePendingConfig(width, height, facing)
vm.previewPendingAt(x, y)
vm.commitPendingAt(x, y)
vm.cancelPending()

vm.placeObstacleDirect(obstacleId, x, y, width, height, facing)
vm.previewMovePlaced(protocolId, x, y)
vm.movePlaced(protocolId, x, y)
vm.removePlaced(protocolId)

vm.selectObstacle(protocolId)
vm.setPlacedFacing(protocolId, facing)
vm.updatePlacedObstacleDirect(protocolId, x, y, facing)
vm.resetObstacleImage(protocolId)
vm.clearAllDetectedImages()
```

---

### 4. Robot Controls
Manual movement commands are sent through the ViewModel.

Main methods:

```kotlin
vm.sendMoveForward()
vm.sendMoveBackward()
vm.sendTurnLeft()
vm.sendTurnRight()
vm.sendStop()
```

Raw commands can also be sent for debugging:

```kotlin
vm.sendRaw("...")
```

---

### 5. Exploration and Fastest Path
The Android app can trigger both exploration and fastest-path execution.

Main methods:

```kotlin
vm.sendStartExploration()
vm.sendStartFastestPath()
vm.stopCurrentRun()
```

During runs, the UI also shows:

- run timer
- execution mode
- playback path trail
- image detections

UI reads:

- `state.executionMode`
- `state.runSeconds`

---

### 6. Playback Visualization
For demo and playback visualization, the app supports:

- command-based playback execution
- robot movement animation
- path trail rendering
- pause/resume when waiting for image detection

Internally this is driven by command batches and playback queue logic in `MainViewModel`.

UI reads:

- `state.playbackPath`

---

### 7. Image Detection
When the robot/RPi sends detections, the app can:

- update obstacle labels with detected target IDs
- store and display detected images
- show all detected images in a popup window

UI reads:

- `state.obstacleImages`
- `state.selectedObstacleId`
- `state.lastImageBytes`
- `state.placedObstacles.targetId`

---

### 8. Logs and Status
The controller screen includes a live chat/log area for:

- sent commands
- received messages
- status updates
- image detection events
- debug information

UI reads:

- `state.statusText`
- `state.log`

---

## Current UI Screens

### Connection Screen
Used for:
- scanning
- pairing
- connecting/disconnecting
- Bluetooth logs

### Controller Screen
Used for:
- arena display
- obstacle interaction
- robot controls
- run controls
- timer
- log/chat area
- obstacle image/details dialog

---

## Architecture Notes

The Android app follows a ViewModel-centered architecture:

- `MainViewModel` handles orchestration
- reducer classes handle state transformation
- `ArenaView` handles custom rendering and gesture interaction
- protocol parsing is isolated in the `protocol` package
- Bluetooth transport is isolated in `BluetoothManager`

---

## Important Notes

- Do not call Bluetooth APIs directly from the UI
- Do not build outgoing protocol strings inside fragments/views
- Use `MainViewModel` methods for all robot, obstacle, and Bluetooth actions
- Image rendering and obstacle detection state are separate concerns
- Resetting the system should also clear path trail, run timer, and detected images

---
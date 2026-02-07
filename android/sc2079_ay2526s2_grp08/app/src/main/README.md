# Methods Implementation

This document explains how the UI should interact with the backend via MainViewModel.

## Core rule

- UI only calls MainViewModel methods and observes state: StateFlow<AppState)
- UI **must not** touch BluetoothManager directly
- UI **must not** build/parse protocol strings

## All UI screens should observe:

```
state.mode / state.conn
Bluetooth connection state (server/client, connected/disconnected)

state.statusText
Status banner text (connection updates + incoming MSG/STATUS)

state.pairedDevices / state.scannedDevices / state.isScanning
Device list UI

state.arena
Arena cells for drawing grid + obstacles

state.robot
Robot pose for drawing robot overlay

state.obstacleBlocks
Obstacle list UI (IDs, coordinates, facing, detected targetId)

state.taggedObstacleRects / state.obstacleGroupMeta
Group tagging UI for algorithm input

state.detections / state.lastDetection
Image detection UI (history + last detected)

state.pathExecution
Path visualization + stepping controls

state.log
Message log (IN/OUT/INFO/ERROR)
```

## Screen → VM method mapping
### 1) Bluetooth / Connection Screen

```
Start listening (server mode)
vm.startDefaultListening()

Disconnect and return to listening
vm.disconnectAndReturnToListening()

Refresh paired devices
vm.refreshPairedDevices()

Start scan
vm.startScan()

Stop scan
vm.stopScan()

Clear scan results
vm.clearScanResults()

Connect to a selected device
vm.connectToDevice(selectedBtDevice)

Discoverable prompt
intent = vm.getDiscoverableIntent(300) then startActivity(intent)

Bluetooth checks
vm.isBluetoothSupported()
vm.isBluetoothEnabled()

UI should display:
paired list from state.pairedDevices
scanned list from state.scannedDevices
loading indicator from state.isScanning
connection status from state.conn
```

### 2) Arena Screen (grid + robot + obstacles)

```
Arena init/reset
vm.initializeArena(width, height)

Robot manual placement (drag/drop)
While dragging (UI-only): vm.setLocalRobotPosition(x, y, dir)
If user confirms and wants remote to follow: vm.sendSetRobotPosition(x, y, dir)

Obstacle placement (tap / drag)
Place or drag obstacle with fixed ID
vm.placeOrMoveObstacle(id, x, y)

Auto-place (let VM choose ID)
val id = vm.sendAddObstacle(x, y) (returns “B#”)

Remove obstacle
vm.removeObstacle(id)

Obstacle face annotation (dropdown N/E/S/W)
vm.setObstacleFacing(id, facing)

UI should draw:
grid using state.arena
robot using state.robot
obstacles either via state.arena (cell flags) or state.obstacleBlocks
detected imageId on obstacle from state.obstacleBlocks.targetId
```

3) Manual Movement Controls

```
Buttons call:
Forward: vm.sendMoveForward()
Backward: vm.sendMoveBackward()
Left: vm.sendTurnLeft()
Right: vm.sendTurnRight()
Stop: vm.sendStop()

Optional “steps” UI:
vm.sendMoveForward(steps)
vm.sendMoveBackward(steps)
vm.sendTurnDegrees(degrees)
```

Notes:
- VM applies local preview immediately, then sends Bluetooth command.

### 4) Algorithm Controls
```
Request sync/state from remote: vm.sendRequestSync()
Start exploration: vm.sendStartExploration()
Start fastest path: vm.sendStartFastestPath()
```

### 5) Group Tagging (for algorithm rectangles)

Use when user is selecting clustered obstacles (component tagging).

```
Assign group ID based on a tapped cell
vm.assignGroupIdFromCell(cellX, cellY, groupId)

Set metadata per group
vm.setGroupMeta(groupId, imageId, facing)

Send all tagged rectangles to algorithm
vm.sendTaggedObstaclesToAlgo()

UI should display:
list of rects from state.taggedObstacleRects
per group metadata from state.obstacleGroupMeta[groupId]
```

### 6) Path Playback / Visualization

When remote sends a path, VM updates `state.pathExecution.poses`.

```
UI controls:
Clear path: vm.clearPath()
Step forward: vm.stepPathForward()
Step backward: vm.stepPathBackward()
Toggle playback: vm.togglePathPlayback() (only useful if autoplay exists)
```

### 7) Detections

Clear detections panel: `vm.clearDetections()`
```
UI reads:
state.lastDetection
state.detections
```

### 8) Logs / Debug

Clear log: `vm.clearLog()`

Send raw debug command: `vm.sendRaw("...")`

Send status: `vm.sendStatus("...")`

UI reads:
`state.log`   

## Common gotchas

- Don’t call scan while connected (BluetoothManager will reject).
- Don’t call direct Bluetooth APIs from UI.
- Don’t build protocol strings in UI — use VM methods.
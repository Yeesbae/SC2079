package com.example.sc2079_ay2526s2_grp08.domain

import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager

/**
 * Represents the robot's current state on the arena.
 *
 * @param x Grid x-coordinate (0-indexed from left)
 * @param y Grid y-coordinate (0-indexed from top)
 * @param directionDeg Orientation in degrees (0=North, 90=East, 180=South, 270=West)
 * @param robotX Robot footprint width in grid cells (default 3x3)
 * @param robotY Robot footprint height in grid cells
 */
data class RobotState(
    val x: Int,
    val y: Int,
    val directionDeg: Int,
    val robotX: Int = 4,
    val robotY: Int = 4
) {

    val robotDirection: RobotDirection
        get() = RobotDirection.fromDegrees(directionDeg)
}

enum class RobotDirection {
    NORTH, EAST, SOUTH, WEST;

    companion object {
        fun fromDegrees(deg: Int): RobotDirection {
            val normalized = ((deg % 360) + 360) % 360
            return when {
                normalized < 45 || normalized >= 315 -> NORTH
                normalized < 135 -> EAST
                normalized < 225 -> SOUTH
                else -> WEST
            }
        }
    }
}

/**
 * Represents a single cell in the arena grid.
 *
 * @param isObstacle True if the cell contains an obstacle
 * @param isTarget True if this cell is a target for image recognition
 * @param imageId Detected image ID (from RPI vision), null if none detected
 * @param targetDirection Direction the target faces (for image recognition)
 * @param obstacleId Optional unique identifier for the obstacle
 */
data class Cell(
    val isObstacle: Boolean = false,
    val isTarget: Boolean = false,
    val imageId: String? = null,
    val targetDirection: RobotDirection? = null,
    val obstacleId: Int? = null,
    val protocolId: String? = null
) {
    companion object { val EMPTY = Cell() }
}

/**
 * Represents the arena grid state.
 *
 * @param width Arena width in cells
 * @param height Arena height in cells
 * @param cells 2D grid stored as row-major array (index = y * width + x)
 */
data class ArenaState(
    val width: Int,
    val height: Int,
    val cells: List<Cell>
) {
    init {
        require(cells.size == width * height) {
            "Cell count ${cells.size} doesn't match dimensions ${width}x${height}"
        }
    }

    /** Get cell at (x, y), returns EMPTY for out-of-bounds */
    fun getCell(x: Int, y: Int): Cell {
        if (x !in 0 until width || y !in 0 until height) return Cell.EMPTY
        return cells[y * width + x]
    }

    fun withCell(x: Int, y: Int, cell: Cell): ArenaState {
        if (x !in 0 until width || y !in 0 until height) return this
        val mutable = cells.toMutableList()
        mutable[y * width + x] = cell
        return copy(cells = mutable)
    }

    companion object {
        /** Default arena dimensions */
        const val DEFAULT_WIDTH = ArenaConfig.GRID_SIZE
        const val DEFAULT_HEIGHT = ArenaConfig.GRID_SIZE

        fun empty(width: Int = DEFAULT_WIDTH, height: Int = DEFAULT_HEIGHT): ArenaState {
            return ArenaState(width, height, List(width * height) { Cell.EMPTY })
        }

        fun fromObstacleArray(width: Int, height: Int, obstacles: BooleanArray): ArenaState {
            val cells = obstacles.map { Cell(isObstacle = it) }
            return ArenaState(width, height, cells)
        }
    }
}

data class GridPoint(val x: Int, val y: Int)

/**
 * Represents an image detection result from RPI vision module.
 *
 * @param imageId Detected image/object identifier
 * @param x Grid x-coordinate where detected (optional)
 * @param y Grid y-coordinate where detected (optional)
 * @param confidence Detection confidence score (0.0-1.0, optional), ignore if not needed
 * @param label Human-readable label for the detected object
 */
data class ImageDetection(
    val imageId: String,
    val x: Int? = null,
    val y: Int? = null,
    val confidence: Float? = null,
    val label: String? = null
)

/**
 * Represents a path execution state for algorithm playback.
 */
enum class ExecutionMode {
    NONE,
    EXPLORATION,
    FASTEST,
}

data class LogEntry(
    val kind: Kind,
    val text: String,
    val timestamp: Long = System.currentTimeMillis()
) {
    enum class Kind { INFO, IN, OUT, ERROR }
}

/**
 * Represents an obstacle block in the arena.
 * MDP uses 8 numbered obstacles (1-8).
 *
 * @param id Obstacle number (1-8)
 * @param x Grid x-coordinate
 * @param y Grid y-coordinate
 * @param facing Direction the target face is pointing (N/E/S/W), null if not set
 * @param targetId Detected image ID after TARGET message, null if not detected yet
 */

data class PendingObstacle(
    val obstacleId: Int,
    val width: Int = 2,
    val height: Int = 2,
    val facing: RobotDirection? = RobotDirection.NORTH
)

data class PlacedObstacle(
    val protocolId: String,
    val obstacleId: Int,
    val bottomLeftX: Int,
    val bottomLeftY: Int,
    val width: Int,
    val height: Int,
    val facing: RobotDirection?,
    val targetId: String? = null
)


object ArenaConfig {
    const val GRID_SIZE = 40
    const val MAX_OBSTACLES = 8
}

data class BtDevice(
    val name: String?,
    val address: String,
    val bonded: Boolean
) {
    val label: String get() = (name ?: "Unknown") + " ($address)"
}


// ─────────────────────────────────────────────────────────────────────────────
// App State (Single Source of Truth)
// ─────────────────────────────────────────────────────────────────────────────

data class AppState(
    // Bluetooth connection
    val mode: BluetoothManager.Mode = BluetoothManager.Mode.NONE,
    val conn: BluetoothManager.State = BluetoothManager.State.DISCONNECTED,
    val statusText: String? = null,

    //Device List
    val pairedDevices: List<BtDevice> = emptyList(),
    val scannedDevices: List<BtDevice> = emptyList(),
    val isScanning: Boolean = false,

    // Robot state
    val robot: RobotState? = null,

    // Arena grid (for rendering and collision)
    val arena: ArenaState? = null,

    val pendingObstacle: PendingObstacle? = null,
    val pendingPreview: PlacedObstacle? = null,
    val dragPreview: PlacedObstacle? = null,
    val placedObstacles: List<PlacedObstacle> = emptyList(),

    val usedTargetObstacleIds: Set<Int> = emptySet(),

    // Image detections
    val detections: List<ImageDetection> = emptyList(),
    val lastDetection: ImageDetection? = null,
    val obstacleImages: Map<String, ByteArray> = emptyMap(),
    val selectedObstacleId: String? = null,
    val lastImageBytes: ByteArray? = null,

    // Path execution
    val playbackPath: List<GridPoint> = emptyList(),
    val executionMode: ExecutionMode = ExecutionMode.NONE,
    val runSeconds: Long = 0,

    // Message log
    val log: List<LogEntry> = emptyList()
)

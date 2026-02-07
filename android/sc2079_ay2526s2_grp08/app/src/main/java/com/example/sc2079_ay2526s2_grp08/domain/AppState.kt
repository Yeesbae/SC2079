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
    val robotX: Int = 3,
    val robotY: Int = 3
) {

    val robotDirection: RobotDirection
        get() = RobotDirection.fromDegrees(directionDeg)

    fun occupies(cellX: Int, cellY: Int): Boolean {
        val halfW = robotX / 2
        val halfH = robotY / 2
        return cellX in (x - halfW)..(x + halfW) &&
               cellY in (y - halfH)..(y + halfH)
    }
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
    val obstacleId: Int? = null
) {
    companion object {
        val EMPTY = Cell()
    }
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

    fun isObstacle(x: Int, y: Int): Boolean = getCell(x, y).isObstacle
    fun isTarget(x: Int, y: Int): Boolean = getCell(x, y).isTarget
    fun getImageId(x: Int, y: Int): String? = getCell(x, y).imageId
    fun withCell(x: Int, y: Int, cell: Cell): ArenaState {
        if (x !in 0 until width || y !in 0 until height) return this
        val mutable = cells.toMutableList()
        mutable[y * width + x] = cell
        return copy(cells = mutable)
    }

    fun setObstacle(x: Int, y: Int, present: Boolean, obstacleId: Int? = null): ArenaState {
        val current = getCell(x, y)
        return withCell(x, y, current.copy(isObstacle = present, obstacleId = if (present) obstacleId else null))
    }

    fun setTarget(x: Int, y: Int, present: Boolean, direction: RobotDirection? = null): ArenaState {
        val current = getCell(x, y)
        return withCell(x, y, current.copy(isTarget = present, targetDirection = if (present) direction else null))
    }

    fun setImageId(x: Int, y: Int, imageId: String?): ArenaState {
        val current = getCell(x, y)
        return withCell(x, y, current.copy(imageId = imageId))
    }

    fun getObstacles(): List<Triple<Int, Int, Int?>> {
        return cells.mapIndexedNotNull { idx, cell ->
            if (cell.isObstacle) {
                val x = idx % width
                val y = idx / width
                Triple(x, y, cell.obstacleId)
            } else null
        }
    }

    fun getTargets(): List<Triple<Int, Int, RobotDirection?>> {
        return cells.mapIndexedNotNull { idx, cell ->
            if (cell.isTarget) {
                val x = idx % width
                val y = idx / width
                Triple(x, y, cell.targetDirection)
            } else null
        }
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

// ─────────────────────────────────────────────────────────────────────────────
// Path Execution Model
// ─────────────────────────────────────────────────────────────────────────────

data class RobotPose(
    val x: Int,
    val y: Int,
    val directionDeg: Int
)

/**
 * Represents a path execution state for algorithm playback.
 *
 * @param poses Sequence of robot poses to execute
 * @param currentIndex Current position in the path (-1 if not started)
 * @param isPlaying Whether path is currently playing
 * @param speed Playback speed multiplier (1.0 = normal)
 */
data class PathExecutionState(
    val poses: List<RobotPose> = emptyList(),
    val currentIndex: Int = -1,
    val isPlaying: Boolean = false,
) {
    val isActive: Boolean get() = poses.isNotEmpty()
    val isComplete: Boolean get() = currentIndex >= poses.lastIndex
    val currentPose: RobotPose? get() = poses.getOrNull(currentIndex)
    val progress: Float get() = if (poses.isEmpty()) 0f else (currentIndex + 1).toFloat() / poses.size
}

data class LogEntry(
    val kind: Kind,
    val text: String,
    val timestamp: Long = System.currentTimeMillis()
) {
    enum class Kind { INFO, IN, OUT, ERROR }
}

// ─────────────────────────────────────────────────────────────────────────────
// Obstacle Model (Separate list for easy UI access)
// ─────────────────────────────────────────────────────────────────────────────

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
data class ObstacleState(
    val id: Int,
    val x: Int,
    val y: Int,
    val facing: RobotDirection? = null,
    val targetId: String? = null
) {
    /** Obstacle ID as string (e.g., "B1", "B2") */
    val obstacleId: String get() = "B$id"
}

data class TaggedObstacleRectModel(
    val groupId: Int,
    val bottomLeftX: Int,
    val bottomLeftY: Int,
    val width: Int,
    val height: Int,
    val imageId: String? = null,
    val facing: RobotDirection? = null
)

data class ObstacleGroupMeta(
    val groupId: Int,                 // 1..8
    val imageId: String? = null,
    val facing: RobotDirection? = null
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

    // Obstacle blocks (for easy UI access - MDP uses 8 obstacles)
    val obstacleBlocks: List<ObstacleState> = emptyList(),
    val taggedObstacleRects: List<TaggedObstacleRectModel> = emptyList(),
    val obstacleGroupMeta: Map<Int, ObstacleGroupMeta> = emptyMap(),

    // Image detections
    val detections: List<ImageDetection> = emptyList(),
    val lastDetection: ImageDetection? = null,

    // Path execution
    val pathExecution: PathExecutionState = PathExecutionState(),

    // Message log
    val log: List<LogEntry> = emptyList()
)

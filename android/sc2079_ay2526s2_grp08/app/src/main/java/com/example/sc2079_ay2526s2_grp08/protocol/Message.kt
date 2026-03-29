package com.example.sc2079_ay2526s2_grp08.protocol

import com.example.sc2079_ay2526s2_grp08.domain.RobotDirection

sealed interface Incoming {

    data class RobotPosition(val x: Int, val y: Int, val direction: RobotDirection) : Incoming

    data class TargetDetected(val obstacleId: String, val targetId: String, val face: RobotDirection?) : Incoming

    data class StatusUpdate(val message: String) : Incoming

    data class GridHex(val hex: String) : Incoming
    data class GridBinary(val width: Int, val height: Int, val cells: BooleanArray) : Incoming
    data class ArenaResize(val width: Int, val height: Int) : Incoming

    data class ObstacleUpdate(val obstacleId: String, val x: Int, val y: Int, val targetFace: RobotDirection? = null) : Incoming
    data class ObstacleRemoved(val obstacleId: String) : Incoming

    data class CommandBatch(val commands: List<String>) : Incoming
    object PlaybackFinished : Incoming

    data class Raw(val line: String) : Incoming
}

sealed interface Outgoing {

    object MoveForward : Outgoing
    object MoveBackward : Outgoing
    object TurnLeft : Outgoing
    object TurnRight : Outgoing

    /** Forward with step count (optional extension) */
    data class MoveForwardSteps(val steps: Int) : Outgoing

    /** Backward with step count (optional extension) */
    data class MoveBackwardSteps(val steps: Int) : Outgoing

    /** Turn by specific angle in degrees (optional extension) */
    data class TurnDegrees(val degrees: Int) : Outgoing

    object StopRobot : Outgoing

    data class ConfigButton(val buttonId: Int, val command: String) : Outgoing
    data class SendStatus(val status: String) : Outgoing

    data class Raw(val line: String) : Outgoing
}

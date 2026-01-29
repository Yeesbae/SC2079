package com.example.sc2079_ay2526s2_grp08.protocol

import com.example.sc2079_ay2526s2_grp08.domain.RobotDirection
import com.example.sc2079_ay2526s2_grp08.domain.RobotPose

sealed interface Incoming {

    data class RobotPosition(
        val x: Int,
        val y: Int,
        val direction: RobotDirection
    ) : Incoming {
        /** Direction as degrees (0=N, 90=E, 180=S, 270=W) */
        val directionDeg: Int get() = when (direction) {
            RobotDirection.NORTH -> 0
            RobotDirection.EAST -> 90
            RobotDirection.SOUTH -> 180
            RobotDirection.WEST -> 270
        }
    }

    data class TargetDetected(
        val obstacleId: String,         // e.g., "B2", "1", etc.
        val targetId: String,           // The image ID detected (e.g., "11")
        val face: RobotDirection?       // Optional: which face the target was found on
    ) : Incoming

    data class StatusUpdate(val message: String) : Incoming

    data class GridHex(val hex: String) : Incoming
    data class GridBinary(val width: Int, val height: Int, val cells: BooleanArray) : Incoming
    data class ArenaResize(val width: Int, val height: Int) : Incoming

    data class ObstacleUpdate(
        val obstacleId: String,
        val x: Int,
        val y: Int,
        val targetFace: RobotDirection? = null
    ) : Incoming

    data class ObstacleRemoved(val obstacleId: String) : Incoming

    data class PathSequence(val poses: List<RobotPose>) : Incoming
    data class PathStep(val pose: RobotPose) : Incoming
    object PathComplete : Incoming
    object PathAbort : Incoming

    object RequestSync : Incoming

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

    data class AddObstacle(
        val obstacleId: String,     // e.g., "B1", "1"
        val x: Int,
        val y: Int
    ) : Outgoing

    data class RemoveObstacle(val obstacleId: String) : Outgoing

    data class SetObstacleFace(
        val obstacleId: String,
        val face: RobotDirection
    ) : Outgoing

    data class SetRobotPosition(
        val x: Int,
        val y: Int,
        val direction: RobotDirection
    ) : Outgoing

    object RequestArenaInfo : Outgoing

    object StartExploration : Outgoing
    object StartFastestPath : Outgoing
    object StopRobot : Outgoing

    data class ConfigButton(val buttonId: Int, val command: String) : Outgoing
    data class SendStatus(val status: String) : Outgoing

    data class Raw(val line: String) : Outgoing
}

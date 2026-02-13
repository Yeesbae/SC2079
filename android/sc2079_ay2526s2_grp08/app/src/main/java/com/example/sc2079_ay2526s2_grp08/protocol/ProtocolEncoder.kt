package com.example.sc2079_ay2526s2_grp08.protocol

import com.example.sc2079_ay2526s2_grp08.domain.util.DirectionUtil

/**
 * Encodes outgoing messages to protocol strings.
 *
 * This is the ONLY place where protocol strings are constructed.
 * UI should never build protocol strings directly.
 *
 * Protocol formats are based on MDP ARCM requirements and AMD Tool compatibility.
 */
object ProtocolEncoder {

    /** Command string for move forward (AMD Tool default: "f") */
    var cmdForward: String = "f"

    /** Command string for move backward (AMD Tool default: "r") */
    var cmdBackward: String = "r"

    /** Command string for turn left (AMD Tool default: "tl") */
    var cmdTurnLeft: String = "tl"

    /** Command string for turn right (AMD Tool default: "tr") */
    var cmdTurnRight: String = "tr"

    /** Command string for requesting arena info */
    var cmdRequestArena: String = "SEND_ARENA"

    /** Command string for start exploration */
    var cmdStartExploration: String = "START_EXPLORE"

    /** Command string for start fastest path */
    var cmdStartFastestPath: String = "START_FASTEST"

    /** Command string for stop */
    var cmdStop: String = "STOP"


    fun encode(msg: Outgoing): String = when (msg) {
        // Movement commands (C.3)
        is Outgoing.MoveForward -> cmdForward
        is Outgoing.MoveBackward -> cmdBackward
        is Outgoing.TurnLeft -> cmdTurnLeft
        is Outgoing.TurnRight -> cmdTurnRight
        is Outgoing.MoveForwardSteps -> "${cmdForward},${msg.steps}"
        is Outgoing.MoveBackwardSteps -> "${cmdBackward},${msg.steps}"
        is Outgoing.TurnDegrees -> "t,${msg.degrees}"

        // Format: "TAG,B1,bl=(x,y),w=2,h=2,img=11,face=N"
        is Outgoing.TaggedObstacleRect -> {
            val parts = mutableListOf(
                "TAG",
                msg.obstacleId,
                "bl=(${msg.bottomLeftX},${msg.bottomLeftY})",
                "w=${msg.width}",
                "h=${msg.height}"
            )
            msg.imageId?.takeIf { it.isNotBlank() }?.let { parts.add("img=$it") }
            msg.facing?.let { parts.add("face=${DirectionUtil.toProtocolChar(it)}") }
            parts.joinToString(",")
        }

        // Obstacle placement (C.6): "ADD,B1,(10,6)"
        is Outgoing.AddObstacle -> "ADD,${msg.obstacleId},(${msg.x},${msg.y})"

        // Obstacle removal (C.6): "SUB,B1"
        is Outgoing.RemoveObstacle -> "SUB,${msg.obstacleId}"

        // Target face annotation (C.7): "FACE,B2,N"
        is Outgoing.SetObstacleFace -> "FACE,${msg.obstacleId},${DirectionUtil.toProtocolChar(msg.face)}"

        // Robot position
        is Outgoing.SetRobotPosition -> "ROBOT,${msg.x},${msg.y},${DirectionUtil.toProtocolChar(msg.direction)}"

        is Outgoing.TaggedRobotRect -> {
            val face = DirectionUtil.toProtocolChar(msg.facing)
            "ROBOT_TAG,(${msg.bottomLeftX},${msg.bottomLeftY}),${msg.width},${msg.height},$face"
        }

        // Arena request
        is Outgoing.RequestSync -> cmdRequestArena

        // Algorithm control
        is Outgoing.StartExploration -> cmdStartExploration
        is Outgoing.StartFastestPath -> cmdStartFastestPath
        is Outgoing.StopRobot -> cmdStop

        // Configurable buttons (C.8)
        is Outgoing.ConfigButton -> msg.command

        // Status
        is Outgoing.SendStatus -> "STATUS,${msg.status}"

        // Raw passthrough
        is Outgoing.Raw -> msg.line.trim()
    }
}

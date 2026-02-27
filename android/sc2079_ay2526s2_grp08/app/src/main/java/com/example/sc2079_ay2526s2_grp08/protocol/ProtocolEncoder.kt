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
    private fun mag3(n: Int): String = n.coerceIn(0, 999).toString().padStart(3, '0')

    fun encode(msg: Outgoing): String = when (msg) {
        // Movement commands
        is Outgoing.MoveForward -> "SF020"
        is Outgoing.MoveBackward -> "BF005"
        is Outgoing.TurnLeft -> "LF090"
        is Outgoing.TurnRight -> "RF090"
        is Outgoing.MoveForwardSteps -> "SF" + mag3(msg.steps * 5)
        is Outgoing.MoveBackwardSteps -> "BF" + mag3(msg.steps * 5)
        is Outgoing.TurnDegrees -> {
            val deg = kotlin.math.abs(msg.degrees)
            val dir = if (msg.degrees >= 0) "R" else "L"
            "${dir}F${mag3(deg)}"
        }
        is Outgoing.StopRobot -> "SF000"
        is Outgoing.ConfigButton -> msg.command
        is Outgoing.SendStatus -> "M,${msg.status}"
        is Outgoing.Raw -> msg.line.trim()
    }
}

package com.example.sc2079_ay2526s2_grp08.protocol.util

import com.example.sc2079_ay2526s2_grp08.protocol.Outgoing

fun Outgoing.isMoveCommand(): Boolean = when (this) {
    Outgoing.MoveForward,
    Outgoing.MoveBackward,
    Outgoing.TurnLeft,
    Outgoing.TurnRight,
    is Outgoing.MoveForwardSteps,
    is Outgoing.MoveBackwardSteps,
    is Outgoing.TurnDegrees -> true
    else -> false
}
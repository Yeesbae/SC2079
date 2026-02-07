package com.example.sc2079_ay2526s2_grp08.domain.util

import com.example.sc2079_ay2526s2_grp08.domain.RobotDirection

object DirectionUtil {

    fun toDegrees(dir: RobotDirection): Int = when (dir) {
        RobotDirection.NORTH -> 0
        RobotDirection.EAST -> 90
        RobotDirection.SOUTH -> 180
        RobotDirection.WEST -> 270
    }

    fun toProtocolChar(dir: RobotDirection): String = when (dir) {
        RobotDirection.NORTH -> "N"
        RobotDirection.EAST -> "E"
        RobotDirection.SOUTH -> "S"
        RobotDirection.WEST -> "W"
    }

    fun fromProtocolToken(token: String): RobotDirection? {
        val t = token.trim().uppercase()
        return when (t) {
            "N", "NORTH", "0" -> RobotDirection.NORTH
            "E", "EAST", "90" -> RobotDirection.EAST
            "S", "SOUTH", "180" -> RobotDirection.SOUTH
            "W", "WEST", "270" -> RobotDirection.WEST
            else -> token.toIntOrNull()?.let { RobotDirection.fromDegrees(it) }
        }
    }
}

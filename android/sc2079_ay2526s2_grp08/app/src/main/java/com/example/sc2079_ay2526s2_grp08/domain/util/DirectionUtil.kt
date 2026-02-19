package com.example.sc2079_ay2526s2_grp08.domain.util

import com.example.sc2079_ay2526s2_grp08.domain.RobotDirection

object DirectionUtil {

    val faces: List<String> = listOf("N","E","S","W")
    val facesString: List<String> = listOf("NORTH","EAST","SOUTH","WEST")
    val degrees: List<Int> = listOf(0,90,180,270)

    fun toDegrees(dir: RobotDirection): Int = when (dir) {
        RobotDirection.NORTH -> degrees[0]
        RobotDirection.EAST -> degrees[1]
        RobotDirection.SOUTH -> degrees[2]
        RobotDirection.WEST -> degrees[3]
    }

    fun toProtocolChar(dir: RobotDirection): String = when (dir) {
        RobotDirection.NORTH -> faces[0]
        RobotDirection.EAST -> faces[1]
        RobotDirection.SOUTH -> faces[2]
        RobotDirection.WEST -> faces[3]
    }

    fun fromProtocolToken(token: String): RobotDirection {
        val t = token.trim().uppercase()
        return when (t) {
            faces[0], facesString[0], degrees[0].toString() -> RobotDirection.NORTH
            faces[1], facesString[1], degrees[1].toString() -> RobotDirection.EAST
            faces[2], facesString[2], degrees[2].toString() -> RobotDirection.SOUTH
            faces[3], facesString[3], degrees[3].toString() -> RobotDirection.WEST
            else -> throw IllegalArgumentException("Invalid direction token: $token")
        }
    }
}

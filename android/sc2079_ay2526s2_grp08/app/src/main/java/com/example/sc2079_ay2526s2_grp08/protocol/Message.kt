package com.example.sc2079_ay2526s2_grp08.protocol

// Incoming messages
sealed interface Incoming {
    data class RobotPosition(val x: Int, val y: Int, val directionDeg: Int) : Incoming
    data class GridHex(val hex: String) : Incoming
    data class GridBinary(val width: Int, val height: Int, val cells: BooleanArray) : Incoming

    data class AddObstacle(val x: Int, val y: Int) : Incoming
    data class RemoveObstacle(val x: Int, val y: Int) : Incoming

    // NEW: Checklist
    data class RobotPose(val x: Int, val y: Int, val dir: String) : Incoming           // "ROBOT,x,y,dir"
    data class Target(val obstacleId: Int, val targetId: Int, val face: String?) : Incoming // "TARGET,id,target[,face]"
    data class Face(val obstacleId: Int, val face: String) : Incoming                 // "FACE,id,dir"

    data class Msg(val text: String) : Incoming
    data class Raw(val line: String) : Incoming
}

// Outgoing messages
sealed interface Outgoing {
    data class Raw(val line: String) : Outgoing
    data class Move(val code: String) : Outgoing
}

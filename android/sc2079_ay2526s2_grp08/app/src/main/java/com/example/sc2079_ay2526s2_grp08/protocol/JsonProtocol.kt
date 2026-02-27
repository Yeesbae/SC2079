package com.example.sc2079_ay2526s2_grp08.protocol

import com.example.sc2079_ay2526s2_grp08.domain.ArenaState
import com.example.sc2079_ay2526s2_grp08.domain.PlacedObstacle
import com.example.sc2079_ay2526s2_grp08.domain.RobotDirection
import com.example.sc2079_ay2526s2_grp08.domain.RobotState
import org.json.JSONArray
import org.json.JSONObject

object JsonProtocol {

    fun toJsonD(dir: RobotDirection): Int = when (dir) {
        RobotDirection.NORTH -> 0
        RobotDirection.EAST  -> 2
        RobotDirection.SOUTH -> 4
        RobotDirection.WEST  -> 6
    }

    fun fromJsonD(d: Int): RobotDirection = when (d) {
        0 -> RobotDirection.NORTH
        2 -> RobotDirection.EAST
        4 -> RobotDirection.SOUTH
        6 -> RobotDirection.WEST
        else -> RobotDirection.NORTH
    }

    fun encodeStartExplore(arena: ArenaState, robot: RobotState, obstacles: List<PlacedObstacle>): String {
        val obj = JSONObject()

        obj.put("cmd", "START_EXPLORE")

        obj.put("grid_size", JSONObject().apply {
            put("x", arena.width)
            put("y", arena.height)
        })

        obj.put("robot", JSONObject().apply {
            put("x", robot.x)
            put("y", robot.y)
            put("d", toJsonD(robot.robotDirection))
        })

        obj.put("obstacles", JSONArray().apply {
            obstacles.forEach { ob ->
                put(JSONObject().apply {
                    put("id", ob.obstacleId ?: -1)
                    put("x", ob.bottomLeftX)
                    put("y", ob.bottomLeftY)
                    put("width", ob.width)
                    put("length", ob.height)
                    put("d", ob.facing?.let { toJsonD(it) } ?: 0)
                })
            }
        })

        return obj.toString()
    }
}
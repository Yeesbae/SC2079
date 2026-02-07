package com.example.sc2079_ay2526s2_grp08.viewmodel.reducers

import com.example.sc2079_ay2526s2_grp08.domain.*
import kotlin.math.abs

/**
 * Pure robot-related state transitions:
 * - ensure robot exists
 * - local movement preview (forward/back/turn)
 * - handle incoming robot position
 *
 * Bluetooth sending is NOT done here.
 */
object RobotReducer {

    fun ensureRobot(state: AppState): AppState {
        if (state.robot != null) return state
        val r = RobotState(x = 1, y = 1, directionDeg = 0)
        return state.copy(robot = r)
    }

    fun setRobotPosition(state: AppState, x: Int, y: Int, directionDeg: Int): AppState {
        val rx = state.robot?.robotX ?: 3
        val ry = state.robot?.robotY ?: 3
        return state.copy(robot = RobotState(x, y, directionDeg, rx, ry))
    }

    fun applyLocalMove(state: AppState, forward: Boolean): AppState {
        val s = ensureRobot(state)
        val robot = s.robot ?: return s

        val step = if (forward) 1 else -1
        val dir = ((robot.directionDeg % 360) + 360) % 360

        val (dx, dy) = when (dir) {
            0 -> 0 to step
            90 -> step to 0
            180 -> 0 to -step
            270 -> -step to 0
            else -> 0 to step
        }

        val gridSize = s.arena?.width ?: ArenaConfig.GRID_SIZE
        val nx = (robot.x + dx).coerceIn(1, gridSize - 2)
        val ny = (robot.y + dy).coerceIn(1, gridSize - 2)

        return s.copy(robot = robot.copy(x = nx, y = ny))
    }

    fun applyLocalTurn(state: AppState, left: Boolean): AppState {
        val s = ensureRobot(state)
        val robot = s.robot ?: return s

        val nextDeg = if (left) (robot.directionDeg + 270) % 360 else (robot.directionDeg + 90) % 360
        return s.copy(robot = robot.copy(directionDeg = nextDeg))
    }

    fun applyLocalTurnDegrees(state: AppState, degrees: Int): AppState {
        val turns = abs((degrees / 90) % 4)
        val left = degrees < 0
        var s = state
        repeat(turns) { s = applyLocalTurn(s, left) }
        return s
    }

    fun onIncomingRobotPosition(state: AppState, x: Int, y: Int, directionDeg: Int): AppState {
        return setRobotPosition(state, x, y, directionDeg)
    }
}

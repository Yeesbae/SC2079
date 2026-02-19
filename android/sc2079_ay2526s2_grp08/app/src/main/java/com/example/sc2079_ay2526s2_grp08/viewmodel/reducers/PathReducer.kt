package com.example.sc2079_ay2526s2_grp08.viewmodel.reducers

import com.example.sc2079_ay2526s2_grp08.domain.*
import com.example.sc2079_ay2526s2_grp08.domain.util.DirectionUtil
import com.example.sc2079_ay2526s2_grp08.protocol.Incoming

/**
 * Pure path execution state transitions.
 * Bluetooth sending is NOT done here.
 */
object PathReducer {

    fun clearPath(state: AppState): AppState {
        return state.copy(pathExecution = PathExecutionState())
    }

    fun togglePlayback(state: AppState): AppState {
        val p = state.pathExecution
        return state.copy(pathExecution = p.copy(isPlaying = !p.isPlaying))
    }

    fun stepForward(state: AppState): AppState {
        val path = state.pathExecution
        if (path.currentIndex >= path.poses.lastIndex) return state

        val nextIndex = path.currentIndex + 1
        val pose = path.poses[nextIndex]
        val rx = state.robot?.robotX ?: 3
        val ry = state.robot?.robotY ?: 3

        return state.copy(
            pathExecution = path.copy(currentIndex = nextIndex),
            robot = RobotState(pose.x, pose.y, DirectionUtil.toDegrees(pose.direction), rx, ry)
        )
    }

    fun stepBackward(state: AppState): AppState {
        val path = state.pathExecution
        if (path.currentIndex <= 0) return state

        val prevIndex = path.currentIndex - 1
        val pose = path.poses[prevIndex]
        val rx = state.robot?.robotX ?: 3
        val ry = state.robot?.robotY ?: 3

        return state.copy(
            pathExecution = path.copy(currentIndex = prevIndex),
            robot = RobotState(pose.x, pose.y, DirectionUtil.toDegrees(pose.direction), rx, ry)
        )
    }

    fun onPathSequence(state: AppState, msg: Incoming.PathSequence): AppState {
        return state.copy(
            pathExecution = PathExecutionState(
                poses = msg.poses,
                currentIndex = -1,
                isPlaying = false,
            )
        )
    }

    fun onPathStep(state: AppState, msg: Incoming.PathStep): AppState {
        val pose = msg.pose
        val rx = state.robot?.robotX ?: 3
        val ry = state.robot?.robotY ?: 3
        return state.copy(robot = RobotState(pose.x, pose.y, DirectionUtil.toDegrees(pose.direction), rx, ry))
    }

    fun onPathComplete(state: AppState): AppState {
        val p = state.pathExecution
        return state.copy(
            pathExecution = p.copy(
                isPlaying = false,
                currentIndex = p.poses.lastIndex
            )
        )
    }

    fun onPathAbort(state: AppState): AppState {
        val p = state.pathExecution
        return state.copy(pathExecution = p.copy(isPlaying = false))
    }
}

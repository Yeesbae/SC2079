package com.example.sc2079_ay2526s2_grp08.viewmodel.reducers

import com.example.sc2079_ay2526s2_grp08.domain.*
import com.example.sc2079_ay2526s2_grp08.protocol.Incoming

/**
 * Pure obstacle-related state transitions.
 * - obstacle placement/move/remove
 * - obstacle facing updates
 * - target detection mapping into obstacles + detections list
 * - incoming obstacle updates/removals
 *
 * NOTE: Bluetooth sending is NOT done here.
 */
object ObstacleReducer {

    fun placeOrMoveObstacle(state: AppState, id: Int, x: Int, y: Int): AppState {
        val filtered = state.obstacleBlocks
            .filterNot { it.id == id }
            .filterNot { it.x == x && it.y == y }

        val existing = state.obstacleBlocks.find { it.id == id }

        val newObs = ObstacleState(
            id = id,
            x = x,
            y = y,
            facing = existing?.facing,
            targetId = existing?.targetId
        )

        return state.copy(obstacleBlocks = filtered + newObs).withArenaDerivedFromObstacleBlocks()
    }

    fun removeObstacle(state: AppState, id: Int): AppState {
        return state.copy(obstacleBlocks = state.obstacleBlocks.filterNot { it.id == id })
            .withArenaDerivedFromObstacleBlocks()
    }

    fun setObstacleFacing(state: AppState, id: Int, facing: RobotDirection?): AppState {
        val updated = state.obstacleBlocks.map { obs ->
            if (obs.id == id) obs.copy(facing = facing) else obs
        }
        return state.copy(obstacleBlocks = updated)
            .withArenaDerivedFromObstacleBlocks()
    }

    fun onIncomingObstacleUpdate(state: AppState, msg: Incoming.ObstacleUpdate): AppState {
        val id = msg.obstacleId.removePrefix("B").toIntOrNull() ?: return state

        val filtered = state.obstacleBlocks
            .filterNot { it.id == id }
            .filterNot { it.x == msg.x && it.y == msg.y }

        val existing = state.obstacleBlocks.find { it.id == id }

        val newObs = ObstacleState(
            id = id,
            x = msg.x,
            y = msg.y,
            facing = msg.targetFace ?: existing?.facing,
            targetId = existing?.targetId
        )

        return state.copy(obstacleBlocks = filtered + newObs)
            .withArenaDerivedFromObstacleBlocks()
    }

    fun onIncomingObstacleRemoved(state: AppState, msg: Incoming.ObstacleRemoved): AppState {
        val id = msg.obstacleId.removePrefix("B").toIntOrNull() ?: return state
        return removeObstacle(state, id)
    }

    fun onTargetDetected(state: AppState, msg: Incoming.TargetDetected): AppState {
        val numericId = msg.obstacleId.removePrefix("B").toIntOrNull()

        val updatedBlocks = state.obstacleBlocks.map { obs ->
            val match = (numericId != null && obs.id == numericId) || obs.obstacleId == msg.obstacleId
            if (match) {
                obs.copy(
                    targetId = msg.targetId,
                    facing = msg.face ?: obs.facing
                )
            } else obs
        }

        val detection = ImageDetection(
            imageId = msg.targetId,
            label = "Obstacle ${msg.obstacleId}"
        )

        val detections = (state.detections + detection).takeLast(100)

        return state.copy(
            obstacleBlocks = updatedBlocks,
            detections = detections,
            lastDetection = detection
        ).withArenaDerivedFromObstacleBlocks()
    }
}
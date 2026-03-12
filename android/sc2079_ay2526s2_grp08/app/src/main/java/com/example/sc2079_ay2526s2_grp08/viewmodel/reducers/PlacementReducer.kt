package com.example.sc2079_ay2526s2_grp08.viewmodel.reducers

import com.example.sc2079_ay2526s2_grp08.domain.*

object PlacementReducer {

    fun setPending(state: AppState, pending: PendingObstacle?): AppState =
        state.copy(pendingObstacle = pending, pendingPreview = null)

    fun setPendingPreview(state: AppState, preview: PlacedObstacle?): AppState =
        state.copy(pendingPreview = preview)

    fun commitPlaced(state: AppState, placed: PlacedObstacle): AppState {
        val nextPlaced = state.placedObstacles.filterNot { it.protocolId == placed.protocolId } + placed

        val nextUsed = state.usedTargetObstacleIds.toMutableSet().apply {
            placed.obstacleId?.let { add(it) }
        }

        return state.copy(
            placedObstacles = nextPlaced,
            usedTargetObstacleIds = nextUsed,
            pendingObstacle = null,
            pendingPreview = null
        ).withArenaDerivedFromPlacedObstacles()
    }

    fun removePlaced(state: AppState, protocolId: String): AppState {
        val removed = state.placedObstacles.find { it.protocolId == protocolId }
        val nextPlaced = state.placedObstacles.filterNot { it.protocolId == protocolId }

        val nextUsed = state.usedTargetObstacleIds.toMutableSet().apply {
            removed?.obstacleId?.let { remove(it) }
        }

        return state.copy(
            placedObstacles = nextPlaced,
            usedTargetObstacleIds = nextUsed
        ).withArenaDerivedFromPlacedObstacles()
    }

    fun updateFacing(state: AppState, protocolId: String, facing: RobotDirection?): AppState {
        val nextPlaced = state.placedObstacles.map {
            if (it.protocolId == protocolId) it.copy(facing = facing) else it
        }
        return state.copy(placedObstacles = nextPlaced).withArenaDerivedFromPlacedObstacles()
    }

    fun onTargetDetected(state: AppState, protocolId: String, targetId: String, face: RobotDirection?): AppState {
        val nextPlaced = state.placedObstacles.map {
            if (it.protocolId == protocolId) it.copy(targetId = targetId, facing = face ?: it.facing) else it
        }
        return state.copy(placedObstacles = nextPlaced).withArenaDerivedFromPlacedObstacles()
    }

    fun resetObstacleImage(state: AppState, protocolId: String): AppState {
        val nextPlaced = state.placedObstacles.map {
            if (it.protocolId == protocolId) {
                it.copy(targetId = null)
            } else it
        }

        val nextImages = state.obstacleImages - protocolId

        return state.copy(
            placedObstacles = nextPlaced,
            obstacleImages = nextImages
        ).withArenaDerivedFromPlacedObstacles()
    }
}

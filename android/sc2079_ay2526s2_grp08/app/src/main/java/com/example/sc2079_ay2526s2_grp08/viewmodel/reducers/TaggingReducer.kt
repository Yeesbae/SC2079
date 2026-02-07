package com.example.sc2079_ay2526s2_grp08.viewmodel.reducers

import com.example.sc2079_ay2526s2_grp08.domain.*
import com.example.sc2079_ay2526s2_grp08.domain.util.ObstacleGrouping

object TaggingReducer {

    fun assignGroupIdFromCell(state: AppState, cellX: Int, cellY: Int, groupId: Int): Pair<AppState, Boolean> {
        val arena = state.arena ?: return state to false

        val component = ObstacleGrouping.floodFillObstacleComponent(arena, cellX, cellY)
        if (component.isEmpty()) return state to false

        val taggedArena = ObstacleGrouping.applyGroupId(arena, groupId, component)

        val bounds = ObstacleGrouping.componentBounds(component) ?: return state to false
        val rect = ObstacleGrouping.componentToAlgoRect(taggedArena, bounds)

        val rectModel = TaggedObstacleRectModel(
            groupId = groupId,
            bottomLeftX = rect.bottomLeftX,
            bottomLeftY = rect.bottomLeftY,
            width = rect.width,
            height = rect.height
        )

        val nextRects = (state.taggedObstacleRects.filterNot { it.groupId == groupId } + rectModel)
            .sortedBy { it.groupId }

        return state.copy(arena = taggedArena, taggedObstacleRects = nextRects) to true
    }

    fun setGroupMeta(state: AppState, groupId: Int, imageId: String?, facing: RobotDirection?): AppState {
        val next = state.obstacleGroupMeta.toMutableMap()
        next[groupId] = ObstacleGroupMeta(groupId, imageId, facing)
        return state.copy(obstacleGroupMeta = next)
    }
}

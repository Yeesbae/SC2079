package com.example.sc2079_ay2526s2_grp08.viewmodel.reducers

import com.example.sc2079_ay2526s2_grp08.domain.*
import com.example.sc2079_ay2526s2_grp08.domain.util.GridCodec
import com.example.sc2079_ay2526s2_grp08.protocol.Incoming

/**
 * Pure arena/grid-related state transitions.
 * Does not mutate obstacleBlocks.
 * only happens when obstacleBlocks changes.
 */
object ArenaReducer {

    fun onGridHex(state: AppState, msg: Incoming.GridHex): AppState {
        val width = state.arena?.width ?: ArenaState.DEFAULT_WIDTH
        val height = state.arena?.height ?: ArenaState.DEFAULT_HEIGHT

        val obstacles = GridCodec.decodeHexToObstacleArray(msg.hex, width, height)
            ?: return state

        return state.copy(arena = ArenaState.fromObstacleArray(width, height, obstacles))
    }

    fun onGridBinary(state: AppState, msg: Incoming.GridBinary): AppState {
        return state.copy(arena = ArenaState.fromObstacleArray(msg.width, msg.height, msg.cells))
    }

    fun onArenaResize(state: AppState, msg: Incoming.ArenaResize): AppState {
        val oldArena = state.arena ?: return state.copy(arena = ArenaState.empty(msg.width, msg.height))

        val newCells = MutableList(msg.width * msg.height) { Cell.EMPTY }

        for (y in 0 until minOf(oldArena.height, msg.height)) {
            for (x in 0 until minOf(oldArena.width, msg.width)) {
                newCells[y * msg.width + x] = oldArena.getCell(x, y)
            }
        }

        return state.copy(arena = ArenaState(msg.width, msg.height, newCells))
    }
}

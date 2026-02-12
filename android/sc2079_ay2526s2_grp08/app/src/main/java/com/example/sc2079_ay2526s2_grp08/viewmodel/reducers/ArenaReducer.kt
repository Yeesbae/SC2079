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
        val arena = state.arena ?: ArenaState.empty()
        val obstacles = GridCodec.decodeHexToObstacleArray(msg.hex, arena.width, arena.height)
            ?: return state

        val merged = mergeObstacleMask(arena, obstacles)
        return state.copy(arena = merged)
    }

    fun onGridBinary(state: AppState, msg: Incoming.GridBinary): AppState {
        val arena = state.arena ?: ArenaState.empty(msg.width, msg.height)
        val resized = if (arena.width != msg.width || arena.height != msg.height) {
            resizeArena(arena, msg.width, msg.height)
        } else arena

        val merged = mergeObstacleMask(resized, msg.cells)
        return state.copy(arena = merged)
    }

    fun onArenaResize(state: AppState, msg: Incoming.ArenaResize): AppState {
        val oldArena = state.arena ?: ArenaState.empty(msg.width, msg.height)
        val resized = resizeArena(oldArena, msg.width, msg.height)
        return state.copy(arena = resized)
    }

    private fun resizeArena(oldArena: ArenaState, newW: Int, newH: Int): ArenaState {
        val newCells = MutableList(newW * newH) { Cell.EMPTY }
        for (y in 0 until minOf(oldArena.height, newH)) {
            for (x in 0 until minOf(oldArena.width, newW)) {
                newCells[y * newW + x] = oldArena.getCell(x, y)
            }
        }
        return ArenaState(newW, newH, newCells)
    }

    private fun mergeObstacleMask(arena: ArenaState, mask: BooleanArray): ArenaState {
        if (mask.size != arena.width * arena.height) return arena

        val next = arena.cells.mapIndexed { idx, cell ->
            val isObs = mask[idx]
            if (isObs) {
                // Ensure isObstacle=true but keep any existing ids/target/facing
                cell.copy(isObstacle = true)
            } else {
                Cell.EMPTY
            }
        }
        return arena.copy(cells = next)
    }
}

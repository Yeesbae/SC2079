package com.example.sc2079_ay2526s2_grp08.domain.util

import com.example.sc2079_ay2526s2_grp08.domain.ArenaState
import com.example.sc2079_ay2526s2_grp08.domain.Cell
import java.util.ArrayDeque

//Flood fill + geometry utilities for obstacle grouping/tagging.
object ObstacleGrouping {

    fun floodFillObstacleComponent(arena: ArenaState, startX: Int, startY: Int): Set<Pair<Int, Int>> {
        if (startX !in 0 until arena.width || startY !in 0 until arena.height) return emptySet()
        if (!arena.getCell(startX, startY).isObstacle) return emptySet()

        val visited = HashSet<Pair<Int, Int>>()
        val q: ArrayDeque<Pair<Int, Int>> = ArrayDeque()

        val start = startX to startY
        visited.add(start)
        q.add(start)

        val dirs = arrayOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)

        while (q.isNotEmpty()) {
            val (x, y) = q.removeFirst()
            for ((dx, dy) in dirs) {
                val nx = x + dx
                val ny = y + dy
                if (nx !in 0 until arena.width || ny !in 0 until arena.height) continue
                if (!arena.getCell(nx, ny).isObstacle) continue

                val p = nx to ny
                if (visited.add(p)) q.add(p)
            }
        }

        return visited
    }

    /**
     * Returns a bounding rectangle (minX/minY,maxX/maxY) of a component.
     */
    fun componentBounds(component: Set<Pair<Int, Int>>): Bounds? {
        if (component.isEmpty()) return null
        val xs = component.map { it.first }
        val ys = component.map { it.second }
        val minX = xs.minOrNull() ?: return null
        val maxX = xs.maxOrNull() ?: return null
        val minY = ys.minOrNull() ?: return null
        val maxY = ys.maxOrNull() ?: return null
        return Bounds(minX, minY, maxX, maxY)
    }

    /**
     * Convert component bounds into algo rectangle:
     * - bottomLeftX = minX
     * - bottomLeftY = (arena.height - 1) - maxY  (y inverted)
     */
    fun componentToAlgoRect(arena: ArenaState, bounds: Bounds): AlgoRect {
        val width = bounds.maxX - bounds.minX + 1
        val height = bounds.maxY - bounds.minY + 1
        val bottomLeftX = bounds.minX
        val bottomLeftY = (arena.height - 1) - bounds.maxY
        return AlgoRect(bottomLeftX, bottomLeftY, width, height)
    }

    /**
     * Apply groupId onto arena cells (writes obstacleId field for the component).
     * Keeps obstacle flags intact.
     */
    fun applyGroupId(arena: ArenaState, groupId: Int, component: Set<Pair<Int, Int>>): ArenaState {
        var updated = arena
        for ((x, y) in component) {
            val c: Cell = updated.getCell(x, y)
            updated = updated.withCell(x, y, c.copy(obstacleId = groupId))
        }
        return updated
    }

    data class Bounds(val minX: Int, val minY: Int, val maxX: Int, val maxY: Int)
    data class AlgoRect(val bottomLeftX: Int, val bottomLeftY: Int, val width: Int, val height: Int)
}

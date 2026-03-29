package com.example.sc2079_ay2526s2_grp08.domain

fun AppState.withArenaDerivedFromPlacedObstacles(): AppState {
    val base = arena ?: ArenaState.empty()

    var a = ArenaState(
        base.width,
        base.height,
        base.cells.map {
            it.copy(
                isObstacle = false,
                isTarget = false,
                imageId = null,
                targetDirection = null,
                obstacleId = null,
                protocolId = null
            )
        }
    )

    fun inBounds(x: Int, y: Int) = x in 0 until a.width && y in 0 until a.height

    for (p in placedObstacles) {
        for (dx in 0 until p.width) for (dy in 0 until p.height) {
            val x = p.bottomLeftX + dx
            val y = p.bottomLeftY + dy
            if (!inBounds(x, y)) continue

            val isTarget = p.obstacleId != null

            val cell = a.getCell(x, y)
            a = a.withCell(
                x, y,
                cell.copy(
                    isObstacle = true,
                    protocolId = p.protocolId,
                    obstacleId = p.obstacleId,
                    isTarget = isTarget,
                    imageId = p.targetId,
                    targetDirection = p.facing
                )
            )
        }
    }

    return copy(arena = a)
}

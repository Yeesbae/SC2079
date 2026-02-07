package com.example.sc2079_ay2526s2_grp08.domain

fun AppState.withArenaDerivedFromObstacleBlocks(): AppState {
    val baseArena = arena ?: ArenaState.empty()

    var updatedArena = ArenaState(
        baseArena.width,
        baseArena.height,
        baseArena.cells.map {
            it.copy(
                isObstacle = false,
                obstacleId = null,
                imageId = null,
                targetDirection = null,
            )
        }
    )

    for (obs in obstacleBlocks) {
        if(obs.x in 0 until updatedArena.width && obs.y in 0 until updatedArena.height){
            val cell = updatedArena.getCell(obs.x, obs.y)
            updatedArena = updatedArena.withCell(
                obs.x,
                obs.y,
                cell.copy(
                    isObstacle = true,
                    obstacleId = obs.id,
                    imageId = obs.targetId,
                    targetDirection = obs.facing
                )
            )
        }
    }
    return copy(arena = updatedArena)
}
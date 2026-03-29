package com.example.sc2079_ay2526s2_grp08.viewmodel

sealed class PlaybackCommand {
    data class MoveForward(val grids: Int) : PlaybackCommand()

    data class MoveBackward(val grids: Int) : PlaybackCommand()

    data class ArcTurn(
        val left: Boolean,
        val front: Boolean
    ) : PlaybackCommand()

    data class Snap(
        val obstacleId: String,
        val face: String
    ) : PlaybackCommand()

    object Finish : PlaybackCommand()
}
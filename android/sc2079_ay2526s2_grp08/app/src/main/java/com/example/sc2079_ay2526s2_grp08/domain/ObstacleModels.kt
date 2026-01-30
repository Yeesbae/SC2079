package com.example.sc2079_ay2526s2_grp08.domain

enum class Facing(val code: String) {
    N("N"), E("E"), S("S"), W("W");

    companion object {
        fun fromCode(code: String): Facing? =
            entries.firstOrNull { it.code.equals(code.trim(), ignoreCase = true) }
    }
}

data class ObstacleState(
    val id: Int,           // 1..8
    val x: Int,            // 0..GRID-1
    val y: Int,            // 0..GRID-1
    val facing: Facing? = null,   // face direction for image/target side
    val targetId: Int? = null     // target id shown on obstacle after TARGET msg
)

package com.example.sc2079_ay2526s2_grp08.domain.util

object GridCodec {
    /**
     * Decode a hex string into a BooleanArray of length width*height.
     * Bits are read high-to-low per nibble, left-to-right across the string.
     *
     * Returns null if invalid hex.
     */
    fun decodeHexToObstacleArray(hex: String, width: Int, height: Int): BooleanArray? {
        val clean = hex.trim().lowercase()
        if (clean.isEmpty()) return null

        val totalBits = width * height
        val out = BooleanArray(totalBits)

        var bitIndex = 0
        for (ch in clean) {
            val nibble = ch.digitToIntOrNull(16) ?: return null
            for (shift in 3 downTo 0) {
                if (bitIndex >= totalBits) return out
                val bit = (nibble shr shift) and 1
                out[bitIndex] = (bit == 1)
                bitIndex++
            }
        }
        return out
    }
}

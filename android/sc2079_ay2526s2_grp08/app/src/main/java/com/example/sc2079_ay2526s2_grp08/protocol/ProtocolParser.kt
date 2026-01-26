package com.example.sc2079_ay2526s2_grp08.protocol

import org.json.JSONArray
import org.json.JSONObject

object ProtocolParser {

    fun parse(line: String): Incoming {
        val raw = line.trim()
        if (raw.isEmpty()) return Incoming.Raw(line)

        if (raw.startsWith("{") && raw.endsWith("}")) {
            parseJson(raw)?.let { return it }
        }

        parseSimple(raw)?.let { return it }

        parseGrid(raw)?.let { return it }

        return Incoming.Raw(line)
    }

    private fun parseJson(raw: String): Incoming? {
        return try {
            val obj = JSONObject(raw)

            if (obj.has("robotPosition")) {
                val arr: JSONArray = obj.getJSONArray("robotPosition")
                if (arr.length() >= 3) {
                    val x = arr.getInt(0)
                    val y = arr.getInt(1)
                    val d = arr.getInt(2)
                    return Incoming.RobotPosition(x, y, d)
                }
            }

            if (obj.has("grid")) {
                val hex = obj.getString("grid").trim()
                if (hex.isNotEmpty()) return Incoming.GridHex(hex)
            }

            null
        } catch (_: Exception) {
            null
        }
    }

    private fun parseSimple(raw: String): Incoming? {
        val upper = raw.uppercase()

        if (upper.startsWith("ROBOTPOSITION:")) {
            val payload = raw.substringAfter(":", "").trim()
            val nums = payload.split(",").map { it.trim() }
            if (nums.size >= 3) {
                val x = nums[0].toIntOrNull() ?: return null
                val y = nums[1].toIntOrNull() ?: return null
                val d = nums[2].toIntOrNull() ?: return null
                return Incoming.RobotPosition(x, y, d)
            }
            return null
        }

        if (upper.startsWith("ADDOBSTACLE:")) {
            val payload = raw.substringAfter(":", "").trim()
            val nums = payload.split(",").map { it.trim() }
            if (nums.size >= 2) {
                val x = nums[0].toIntOrNull() ?: return null
                val y = nums[1].toIntOrNull() ?: return null
                return Incoming.AddObstacle(x, y)
            }
            return null
        }

        if (upper.startsWith("REMOVEOBSTACLE:")) {
            val payload = raw.substringAfter(":", "").trim()
            val nums = payload.split(",").map { it.trim() }
            if (nums.size >= 2) {
                val x = nums[0].toIntOrNull() ?: return null
                val y = nums[1].toIntOrNull() ?: return null
                return Incoming.RemoveObstacle(x, y)
            }
            return null
        }

        return null
    }

    private fun parseGrid(raw: String): Incoming? {
        val parts = raw.split(Regex("\\s+")).filter { it.isNotBlank() }
        if (parts.isEmpty()) return null
        if (parts[0].uppercase() != "GRID") return null

        // GRID h w robotX robotY robotDir [cells...]
        if (parts.size < 6) return null

        val h = parts[1].toIntOrNull() ?: return null
        val w = parts[2].toIntOrNull() ?: return null

        val rx = parts[3].toIntOrNull() ?: return null
        val ry = parts[4].toIntOrNull() ?: return null
        val rd = parts[5].toIntOrNull() ?: return null

        val cellCount = w * h
        val cells = BooleanArray(cellCount)
        val start = 6

        val max = minOf(cellCount, parts.size - start)
        for (i in 0 until max) {
            val v = parts[start + i].toIntOrNull() ?: 0
            cells[i] = (v != 0)
        }


        return Incoming.GridBinary(w, h, cells).also {}
    }
}

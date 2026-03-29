package com.example.sc2079_ay2526s2_grp08.protocol

import com.example.sc2079_ay2526s2_grp08.domain.RobotDirection
import com.example.sc2079_ay2526s2_grp08.domain.util.DirectionUtil
import org.json.JSONArray
import org.json.JSONObject

/**
 * Parses incoming protocol messages from AMD Tool, Robot, and RPI.
 *
 * Based on MDP ARCM Checklist:
 * - C.9:  "TARGET,<obstacle>,<targetId>" or "TARGET,<obstacle>,<targetId>,<face>"
 * - C.10: "ROBOT,<x>,<y>,<direction>" where direction is N,S,E,W
 * - C.4:  "MSG,[status text]"
 *
 * Also supports:
 * - JSON format (from AMD Tool custom scripts)
 */
object ProtocolParser {

    fun parse(raw: String): Incoming {
        val line = raw.trim()
        if (line.isEmpty()) return Incoming.Raw(raw)

        if (line.startsWith("COMMANDS:")) {

            val json = line.removePrefix("COMMANDS:")
            val arr = JSONArray(json)

            val cmds = mutableListOf<String>()

            for (i in 0 until arr.length()) {
                cmds.add(arr.getString(i))
            }

            return Incoming.CommandBatch(cmds)
        }

        // Try JSON first
        if (line.startsWith("{") && line.endsWith("}")) {
            parseJson(line)?.let { return it }
        }

        // Try MDP protocol formats
        parseMdpProtocol(line)?.let { return it }

        // Try legacy grid format
        parseGrid(line)?.let { return it }

        return Incoming.Raw(line)
    }

    private fun parseMdpProtocol(raw: String): Incoming? {
        val parts = raw.split(",").map { it.trim() }
        if (parts.isEmpty()) return null

        val command = parts[0].uppercase()

        return when (command) {

            // Compact Robot position: "R,x,y,d"
            "ROBOT" -> parseRobotPosition(parts)
            "R" -> parseRobotPosition(parts)

            // Compact Target detection: "T,B2,11,N"
            "TARGET" -> parseTargetDetected(parts)

            "MSG" -> parseStatusMessage(raw)
            "STATUS" -> if (parts.size >= 2) Incoming.StatusUpdate(parts.drop(1).joinToString(",")) else null
            "M" -> Incoming.StatusUpdate(parts.drop(1).joinToString(","))

            // Compact Explore start echo
            "E" -> Incoming.StatusUpdate("Exploration started")

            // Compact Fastest start echo
            "F" -> Incoming.StatusUpdate("Fastest path started")

            else -> null
        }
    }


    /**
     * Parse robot position: "ROBOT,<x>,<y>,<direction>"
     * Direction can be: N, S, E, W (or NORTH, SOUTH, EAST, WEST)
     */
    private fun parseRobotPosition(parts: List<String>): Incoming? {
        if (parts.size < 4) return null
        val x = parts[1].toIntOrNull() ?: return null
        val y = parts[2].toIntOrNull() ?: return null
        val direction = parseDirection(parts[3]) ?: return null
        return Incoming.RobotPosition(x, y, direction)
    }

    /**
     * Parse target detection: "TARGET,<obstacle>,<targetId>[,<face>]"
     * Example: "TARGET,B2,11" or "TARGET,B2,11,N"
     */
    private fun parseTargetDetected(parts: List<String>): Incoming? {
        if (parts.size < 3) return null
        if (parts[0].equals("TARGET", ignoreCase = true) && parts[1].equals("DONE", ignoreCase = true) && parts[2].equals("FIN", ignoreCase = true)) {
            return Incoming.PlaybackFinished
        }
        val obstacleId = if (parts[1].startsWith("B")) parts[1] else "B${parts[1]}"
        val targetId = parts[2]
        val face = if (parts.size >= 4) parseDirection(parts[3]) else null
        return Incoming.TargetDetected(obstacleId, targetId, face)
    }

    /**
     * Parse status message: "MSG,[text]" or "MSG,text"
     */
    private fun parseStatusMessage(raw: String): Incoming? {
        // Handle "MSG,[text]" format (with brackets)
        val bracketMatch = Regex("MSG,\\[(.*)\\]", RegexOption.IGNORE_CASE).find(raw)
        if (bracketMatch != null) {
            return Incoming.StatusUpdate(bracketMatch.groupValues[1])
        }

        // Handle "MSG,text" format (without brackets)
        val commaIdx = raw.indexOf(',')
        if (commaIdx >= 0 && commaIdx < raw.length - 1) {
            return Incoming.StatusUpdate(raw.substring(commaIdx + 1).trim())
        }

        return null
    }

    private fun parseJson(raw: String): Incoming? {
        return try {
            val obj = JSONObject(raw)

            // Check for type field
            val type = obj.optString("type", "").uppercase()

            when (type) {
                "ROBOT", "ROBOT_POSITION" -> parseJsonRobotPosition(obj)
                "TARGET", "TARGET_DETECTED" -> parseJsonTargetDetected(obj)
                "STATUS", "MSG" -> Incoming.StatusUpdate(obj.optString("message", obj.optString("status", "")))
                "GRID" -> parseJsonGrid(obj)
                "RESIZE", "ARENA_RESIZE" -> parseJsonArenaResize(obj)
                "OBSTACLE", "ADD_OBSTACLE" -> parseJsonObstacle(obj)
                "REMOVE_OBSTACLE" -> Incoming.ObstacleRemoved(obj.optString("id", obj.optString("obstacleId", "")))
                else -> parseJsonByContent(obj)
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun parseJsonByContent(obj: JSONObject): Incoming? {
        // Robot position: {"robotPosition": [x, y, dir]}
        if (obj.has("robotPosition")) {
            val arr = obj.getJSONArray("robotPosition")
            if (arr.length() >= 3) {
                val x = arr.getInt(0)
                val y = arr.getInt(1)
                val dir = when {
                    obj.has("d") -> {
                        val dv = obj.optInt("d", 0)
                        when (dv) {
                            0 -> RobotDirection.NORTH
                            2 -> RobotDirection.EAST
                            4 -> RobotDirection.SOUTH
                            6 -> RobotDirection.WEST
                            else -> RobotDirection.NORTH
                        }
                    }
                    else -> {
                        val dStr = obj.optString("direction", obj.optString("dir", "N"))
                        parseDirection(dStr) ?: RobotDirection.NORTH
                    }
                }
                return Incoming.RobotPosition(x, y, dir)
            }
        }

        // Grid hex: {"grid": "hex..."}
        if (obj.has("grid")) {
            val hex = obj.getString("grid").trim()
            if (hex.isNotEmpty()) return Incoming.GridHex(hex)
        }

        // Target detected: {"target": ..., "imageId": ...}
        if (obj.has("target") || obj.has("obstacleId") || obj.has("obstacle")) {
            val obstacleId = obj.optString("obstacleId", obj.optString("obstacle", obj.optString("target", "")))
            val targetId = obj.optString("targetId", obj.optString("imageId", obj.optString("image", "")))
            if (obstacleId.isNotEmpty() && targetId.isNotEmpty()) {
                val face = parseDirection(obj.optString("face", obj.optString("direction", "")))
                return Incoming.TargetDetected(obstacleId, targetId, face)
            }
        }

        // Robot position with named fields: {"x": ..., "y": ..., "direction": ...}
        if (obj.has("x") && obj.has("y") && (obj.has("direction") || obj.has("dir") || obj.has("d"))) {
            val x = obj.getInt("x")
            val y = obj.getInt("y")
            val dirStr = obj.optString("direction", obj.optString("dir", obj.optString("d", "N")))
            val dir = parseDirection(dirStr) ?: RobotDirection.NORTH
            return Incoming.RobotPosition(x, y, dir)
        }

        // Status/Message: {"message": ...} or {"status": ...}
        if (obj.has("message") || obj.has("status")) {
            val msg = obj.optString("message", obj.optString("status", ""))
            if (msg.isNotEmpty()) return Incoming.StatusUpdate(msg)
        }

        return null
    }

    private fun parseJsonRobotPosition(obj: JSONObject): Incoming? {
        return try {
            val x = obj.getInt("x")
            val y = obj.getInt("y")
            val dirStr = obj.optString("direction", obj.optString("dir", "N"))
            val dir = parseDirection(dirStr) ?: RobotDirection.NORTH
            Incoming.RobotPosition(x, y, dir)
        } catch (_: Exception) {
            null
        }
    }

    private fun parseJsonTargetDetected(obj: JSONObject): Incoming? {
        return try {
            val obstacleId = obj.optString("obstacleId", obj.optString("obstacle", ""))
            val targetId = obj.optString("targetId", obj.optString("imageId", ""))
            if (obstacleId.isEmpty() || targetId.isEmpty()) return null
            val face = parseDirection(obj.optString("face", obj.optString("direction", "")))
            Incoming.TargetDetected(obstacleId, targetId, face)
        } catch (_: Exception) {
            null
        }
    }

    private fun parseJsonGrid(obj: JSONObject): Incoming? {
        val hex = obj.optString("grid", obj.optString("data", "")).trim()
        return if (hex.isNotEmpty()) Incoming.GridHex(hex) else null
    }

    private fun parseJsonArenaResize(obj: JSONObject): Incoming? {
        return try {
            Incoming.ArenaResize(obj.getInt("width"), obj.getInt("height"))
        } catch (_: Exception) {
            null
        }
    }

    private fun parseJsonObstacle(obj: JSONObject): Incoming? {
        return try {
            val id = obj.optString("id", obj.optString("obstacleId", ""))
            val x = obj.getInt("x")
            val y = obj.getInt("y")
            val face = parseDirection(obj.optString("face", obj.optString("direction", "")))
            Incoming.ObstacleUpdate(id, x, y, face)
        } catch (_: Exception) {
            null
        }
    }


    private fun parseGrid(raw: String): Incoming? {
        val parts = raw.split(Regex("\\s+")).filter { it.isNotBlank() }
        if (parts.isEmpty()) return null
        if (parts[0].uppercase() != "GRID") return null

        // GRID h w robotX robotY robotDir [cells...]
        if (parts.size < 6) return null

        val h = parts[1].toIntOrNull() ?: return null
        val w = parts[2].toIntOrNull() ?: return null

        val cellCount = w * h
        val cells = BooleanArray(cellCount)
        val start = 6

        val max = minOf(cellCount, parts.size - start)
        for (i in 0 until max) {
            val v = parts[start + i].toIntOrNull() ?: 0
            cells[i] = (v != 0)
        }

        return Incoming.GridBinary(w, h, cells)
    }

    private fun parseDirection(s: String): RobotDirection? = DirectionUtil.fromProtocolToken(s)
}

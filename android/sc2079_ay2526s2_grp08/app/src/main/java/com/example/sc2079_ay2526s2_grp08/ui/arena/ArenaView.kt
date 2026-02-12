package com.example.sc2079_ay2526s2_grp08.ui.arena

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import com.example.sc2079_ay2526s2_grp08.domain.*
import kotlin.math.min

class ArenaView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    interface Listener {
        fun onArenaCellTap(x: Int, y: Int)
        fun onPendingPreview(bottomLeftX: Int, bottomLeftY: Int)
        fun onPendingCommit(bottomLeftX: Int, bottomLeftY: Int)
        fun onPendingCancel()
        fun onPlacedTap(protocolId: String)
        fun onPlacedDrag(protocolId: String, x: Int, y: Int)
        fun onPlacedDrop(protocolId: String, x: Int, y: Int)
        fun onPlacedRemove(protocolId: String)
    }

    private var listener: Listener? = null
    fun setListener(l: Listener?) { listener = l }

    private var arena: ArenaState? = null
    fun setArena(a: ArenaState?){
        arena = a
        invalidate()
    }

    private var pendingActive: Boolean = false
    private var pendingPreview: PlacedObstacle? = null
    private var draggingPending = false
    private var dragPreview: PlacedObstacle? = null

    fun setPendingActive(active: Boolean) {
        pendingActive = active
    }

    fun setPendingPreview(p: PlacedObstacle?) {
        pendingPreview = p
        invalidate()
    }

    fun setDragPreview(p: PlacedObstacle?) { dragPreview = p; invalidate() }


    private val gridSize = ArenaConfig.GRID_SIZE

    var robotX: Int = 1
        set(value) {
            field = value.coerceIn(1, gridSize - 2)
            invalidate()
        }

    var robotY: Int = 1
        set(value) {
            field = value.coerceIn(1, gridSize - 2)
            invalidate()
        }

    private var robotDir: RobotDirection = RobotDirection.NORTH

    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        color = 0xFFCCCCCC.toInt()
        strokeWidth = dp(1f)
    }

    private val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        color = 0xFF000000.toInt()
        strokeWidth = dp(2f)
    }

    private val robotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = 0xFF2196F3.toInt()
    }

    private val axisPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF000000.toInt()
        textSize = dp(10f)
        textAlign = Paint.Align.CENTER
    }

    private val obstaclePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        color = 0xFF455A64.toInt()
    }

    private val obstacleIdPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFFFFFFF.toInt()
        textAlign = Paint.Align.LEFT
        textSize = dp(11f)
        isFakeBoldText = true
    }

    private val targetIdPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFFFFFFF.toInt()
        textAlign = Paint.Align.CENTER
        textSize = dp(16f)
        isFakeBoldText = true
    }

    private val faceStrokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        color = 0xFFFFC107.toInt()
        strokeWidth = dp(3f)
        strokeCap = Paint.Cap.ROUND
    }

    private var sidePx = 0f
    private var cellPx = 0f
    private var originX = 0f
    private var originY = 0f

    private var draggingProtocolId: String? = null
    private var downCellX: Int? = null
    private var downCellY: Int? = null
    private var moved = false

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)

        val usableW = w - paddingLeft - paddingRight
        val usableH = h - paddingTop - paddingBottom
        sidePx = min(usableW, usableH).toFloat()

        originX = paddingLeft + (usableW - sidePx) / 2f
        originY = paddingTop + (usableH - sidePx) / 2f

        cellPx = sidePx / gridSize
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (cellPx <= 0f) return

        val left = originX
        val top = originY
        val right = left + sidePx
        val bottom = top + sidePx

        canvas.drawRect(left, top, right, bottom, borderPaint)

        for (i in 0..gridSize) {
            val x = left + i * cellPx
            val y = top + i * cellPx
            canvas.drawLine(x, top, x, bottom, gridPaint)
            canvas.drawLine(left, y, right, y, gridPaint)
        }

        for (i in 0 until gridSize) {
            val cx = left + (i + 0.5f) * cellPx
            canvas.drawText(i.toString(), cx, bottom + dp(12f), axisPaint)

            val cy = top + (gridSize - i - 0.5f) * cellPx
            canvas.drawText(i.toString(), left - dp(10f), cy + dp(4f), axisPaint)
        }

        val preview = pendingPreview
        if (preview != null) {
            val paint = Paint(obstaclePaint).apply { alpha = 120 } // ghost
            val pxL = left + preview.bottomLeftX * cellPx
            val pxR = left + (preview.bottomLeftX + preview.width) * cellPx
            val pxT = top + (gridSize - 1 - (preview.bottomLeftY + preview.height - 1)) * cellPx
            val pxB = top + (gridSize - preview.bottomLeftY) * cellPx

            canvas.drawRect(pxL, pxT, pxR, pxB, paint)

            // optional preview label
            canvas.drawText(
                preview.protocolId,
                (pxL + pxR) / 2f,
                (pxT + pxB) / 2f + dp(6f),
                targetIdPaint
            )
        }

        val ghost = dragPreview
        if (ghost != null) {
            val paint = Paint(obstaclePaint).apply { alpha = 120 }
            val pxL = left + ghost.bottomLeftX * cellPx
            val pxR = left + (ghost.bottomLeftX + ghost.width) * cellPx
            val pxT = top + (gridSize - 1 - (ghost.bottomLeftY + ghost.height - 1)) * cellPx
            val pxB = top + (gridSize - ghost.bottomLeftY) * cellPx
            canvas.drawRect(pxL, pxT, pxR, pxB, paint)
        }

        val a = arena
        if (a != null) {
            // 1) collect obstacle cells grouped by protocolId
            val groups = mutableMapOf<String, MutableList<Pair<Int, Int>>>()
            val groupMeta = mutableMapOf<String, Cell>()

            for (y in 0 until a.height) {
                for (x in 0 until a.width) {
                    val cell = a.getCell(x, y)
                    if (!cell.isObstacle) continue
                    val pid = cell.protocolId ?: continue

                    groups.getOrPut(pid) { mutableListOf() }.add(x to y)
                    groupMeta.putIfAbsent(pid, cell) // first cell as representative
                }
            }

            // 2) draw each group as a block (single label)
            for ((pid, cells) in groups) {
                // compute bounds
                val minX = cells.minOf { it.first }
                val maxX = cells.maxOf { it.first }
                val minY = cells.minOf { it.second }
                val maxY = cells.maxOf { it.second }

                val pxL = left + minX * cellPx
                val pxR = left + (maxX + 1) * cellPx
                val pxT = top + (gridSize - 1 - maxY) * cellPx
                val pxB = top + (gridSize - minY) * cellPx

                canvas.drawRect(pxL, pxT, pxR, pxB, obstaclePaint)

                val rep = groupMeta[pid]
                val detected = rep?.imageId

                if (!detected.isNullOrBlank()) {
                    // BIG when detected
                    canvas.drawText(
                        detected,
                        (pxL + pxR) / 2f,
                        (pxT + pxB) / 2f + dp(6f),
                        targetIdPaint
                    )
                } else {
                    // SMALL initially
                    val label = rep?.obstacleId?.toString() ?: pid // fallback: pid
                    canvas.drawText(
                        label,
                        pxL + dp(4f),          // small label near top-left
                        pxT + dp(14f),
                        obstacleIdPaint
                    )
                }
            }
        }


        for (dx in -1..1) {
            for (dy in -1..1) {
                val gx = robotX + dx
                val gy = robotY + dy
                if (gx !in 0 until gridSize || gy !in 0 until gridSize) continue

                val px = left + gx * cellPx
                val py = top + (gridSize - 1 - gy) * cellPx
                canvas.drawRect(px, py, px + cellPx, py + cellPx, robotPaint)
            }
        }

        val robotLeft = left + (robotX - 1) * cellPx
        val robotRight = left + (robotX + 2) * cellPx
        val robotTop = top + (gridSize - 1 - (robotY + 1)) * cellPx
        val robotBottom = top + (gridSize - (robotY - 1)) * cellPx

        val headPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            style = Paint.Style.STROKE
            color = 0xFFFFC107.toInt()
            strokeWidth = dp(4f)
            strokeCap = Paint.Cap.ROUND
        }

        when (robotDir) {
            RobotDirection.NORTH -> canvas.drawLine(robotLeft, robotTop, robotRight, robotTop, headPaint)
            RobotDirection.SOUTH -> canvas.drawLine(robotLeft, robotBottom, robotRight, robotBottom, headPaint)
            RobotDirection.EAST -> canvas.drawLine(robotRight, robotTop, robotRight, robotBottom, headPaint)
            RobotDirection.WEST -> canvas.drawLine(robotLeft, robotTop, robotLeft, robotBottom, headPaint)
        }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (cellPx <= 0f) return false

        val cell = pointToCell(event.x, event.y)
        val inArena = cell != null

        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                moved = false
                downCellX = cell?.first
                downCellY = cell?.second

                draggingPending = false
                draggingProtocolId = null

                if (inArena) {
                    val (cx, cy) = cell!!

                    // 1) If tapping on an existing placed obstacle => drag that obstacle
                    val pid = obstacleAt(cx, cy)
                    if (pid != null) {
                        draggingProtocolId = pid
                    } else if (pendingActive) {
                        // 2) Otherwise if we have a pending block => start pending drag
                        draggingPending = true
                        listener?.onPendingPreview(cx, cy)
                    }
                }
                return true
            }

            MotionEvent.ACTION_MOVE -> {
                val c = cell ?: run {
                    moved = true
                    // If finger moved out of arena while dragging pending, you may choose to cancel preview
                    return true
                }

                moved = true

                // Pending drag preview
                if (draggingPending) {
                    listener?.onPendingPreview(c.first, c.second)
                    return true
                }

                // Placed obstacle drag preview
                val pid = draggingProtocolId
                if (pid != null) {
                    listener?.onPlacedDrag(pid, c.first, c.second)
                }
                return true
            }

            MotionEvent.ACTION_UP -> {
                val pid = draggingProtocolId
                val wasPending = draggingPending

                draggingProtocolId = null
                draggingPending = false

                // Pending placement commit/cancel
                if (wasPending) {
                    if (!inArena || cell == null) {
                        listener?.onPendingCancel()
                    } else {
                        listener?.onPendingCommit(cell.first, cell.second)
                    }
                    return true
                }

                // Existing placed obstacle tap/drop/remove
                if (pid != null) {
                    if (!inArena || cell == null) {
                        listener?.onPlacedRemove(pid)
                        return true
                    }

                    val endX = cell.first
                    val endY = cell.second

                    val startX = downCellX
                    val startY = downCellY

                    if (!moved && startX != null && startY != null && startX == endX && startY == endY) {
                        listener?.onPlacedTap(pid)
                    } else {
                        listener?.onPlacedDrop(pid, endX, endY)
                    }
                    return true
                }

                // Normal arena tap (no pending active): let fragment decide what to do
                if (inArena && cell != null) {
                    listener?.onArenaCellTap(cell.first, cell.second)
                }
                return true
            }
        }

        return super.onTouchEvent(event)
    }


    fun setRobotPosition(x: Int, y: Int, dir: RobotDirection) {
        robotX = x
        robotY = y
        robotDir = dir
        invalidate()
    }

    private fun obstacleAt(x: Int, y: Int): String? {
        val a = arena ?: return null
        val c = a.getCell(x, y)
        return if (c.isObstacle) c.protocolId else null
    }

    private fun pointToCell(px: Float, py: Float): Pair<Int, Int>? {
        val left = originX
        val top = originY
        val right = left + sidePx
        val bottom = top + sidePx

        if (px < left || px > right || py < top || py > bottom) return null

        val gx = ((px - left) / cellPx).toInt().coerceIn(0, gridSize - 1)
        val rowFromTop = ((py - top) / cellPx).toInt().coerceIn(0, gridSize - 1)
        val gy = (gridSize - 1 - rowFromTop).coerceIn(0, gridSize - 1)
        return gx to gy
    }

    private fun dp(v: Float): Float = v * resources.displayMetrics.density
}

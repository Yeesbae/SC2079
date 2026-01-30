package com.example.sc2079_ay2526s2_grp08.ui.arena

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import com.example.sc2079_ay2526s2_grp08.domain.ArenaConfig
import com.example.sc2079_ay2526s2_grp08.domain.Facing
import com.example.sc2079_ay2526s2_grp08.domain.ObstacleState
import kotlin.math.min

class ArenaView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    interface Listener {
        fun onCellTap(x: Int, y: Int)
        fun onObstacleTap(obstacleId: Int)
        fun onObstacleDrag(obstacleId: Int, x: Int, y: Int)
        fun onObstacleRemove(obstacleId: Int)
    }

    private var listener: Listener? = null
    fun setListener(l: Listener?) { listener = l }

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

    private var obstacleBlocks: List<ObstacleState> = emptyList()

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

    private var draggingId: Int? = null
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

        for (ob in obstacleBlocks) {
            val gx = ob.x
            val gy = ob.y
            if (gx !in 0 until gridSize || gy !in 0 until gridSize) continue

            val px = left + gx * cellPx
            val py = top + (gridSize - 1 - gy) * cellPx
            val r = px + cellPx
            val b = py + cellPx

            canvas.drawRect(px, py, r, b, obstaclePaint)

            canvas.drawText(ob.id.toString(), px + dp(4f), py + dp(12f), obstacleIdPaint)

            ob.targetId?.let { tid ->
                canvas.drawText(tid.toString(), (px + r) / 2f, (py + b) / 2f + dp(6f), targetIdPaint)
            }

            when (ob.facing) {
                Facing.N -> canvas.drawLine(px, py, r, py, faceStrokePaint)
                Facing.S -> canvas.drawLine(px, b, r, b, faceStrokePaint)
                Facing.E -> canvas.drawLine(r, py, r, b, faceStrokePaint)
                Facing.W -> canvas.drawLine(px, py, px, b, faceStrokePaint)
                null -> Unit
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

                if (inArena) {
                    val hit = obstacleAt(cell!!.first, cell.second)
                    draggingId = hit?.id
                } else {
                    draggingId = null
                }
                return true
            }

            MotionEvent.ACTION_MOVE -> {
                val id = draggingId ?: return true
                val c = cell ?: run {
                    moved = true
                    return true
                }

                moved = true
                listener?.onObstacleDrag(id, c.first, c.second)
                return true
            }

            MotionEvent.ACTION_UP -> {
                val id = draggingId
                val startX = downCellX
                val startY = downCellY
                draggingId = null

                if (id != null) {
                    if (!inArena) {
                        listener?.onObstacleRemove(id)
                        return true
                    }

                    val endX = cell!!.first
                    val endY = cell.second

                    if (!moved && startX != null && startY != null && startX == endX && startY == endY) {
                        listener?.onObstacleTap(id)
                    }
                    return true
                }

                if (inArena) {
                    listener?.onCellTap(cell!!.first, cell.second)
                }
                return true
            }
        }

        return super.onTouchEvent(event)
    }

    fun setRobotPosition(x: Int, y: Int) {
        robotX = x
        robotY = y
    }

    fun setObstacleBlocks(list: List<ObstacleState>) {
        obstacleBlocks = list
        invalidate()
    }

    private fun obstacleAt(x: Int, y: Int): ObstacleState? =
        obstacleBlocks.firstOrNull { it.x == x && it.y == y }

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

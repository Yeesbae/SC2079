package com.example.sc2079_ay2526s2_grp08.ui.arena

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.example.sc2079_ay2526s2_grp08.MainActivity
import com.example.sc2079_ay2526s2_grp08.R
import com.example.sc2079_ay2526s2_grp08.domain.*
import com.example.sc2079_ay2526s2_grp08.domain.util.DirectionUtil
import kotlinx.coroutines.launch

class ArenaFragment : Fragment() {

    private val viewModel by lazy { (requireActivity() as MainActivity).viewModel }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View = inflater.inflate(R.layout.fragment_arena, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val arenaView = view.findViewById<ArenaView>(R.id.arenaView) ?: return
        val tvSelected = view.findViewById<TextView>(R.id.tvSelected) ?: return

        view.findViewById<Button>(R.id.btnObs1)?.setOnClickListener { showObstacleConfigDialog(1) }
        view.findViewById<Button>(R.id.btnObs2)?.setOnClickListener { showObstacleConfigDialog(2) }
        view.findViewById<Button>(R.id.btnObs3)?.setOnClickListener { showObstacleConfigDialog(3) }
        view.findViewById<Button>(R.id.btnObs4)?.setOnClickListener { showObstacleConfigDialog(4) }
        view.findViewById<Button>(R.id.btnObs5)?.setOnClickListener { showObstacleConfigDialog(5) }
        view.findViewById<Button>(R.id.btnObs6)?.setOnClickListener { showObstacleConfigDialog(6) }
        view.findViewById<Button>(R.id.btnObs7)?.setOnClickListener { showObstacleConfigDialog(7) }
        view.findViewById<Button>(R.id.btnObs8)?.setOnClickListener { showObstacleConfigDialog(8) }

        arenaView.setListener(object : ArenaView.Listener {
            override fun onArenaCellTap(x: Int, y: Int) {
                if (viewModel.state.value.pendingObstacle != null) {
                    viewModel.commitPendingAt(x, y)
                }
            }
            override fun onPendingPreview(x: Int, y: Int) {
                viewModel.previewPendingAt(x, y)
            }
            override fun onPendingCommit(x: Int, y: Int) {
                viewModel.commitPendingAt(x, y)
            }
            override fun onPendingCancel() {
                viewModel.cancelPending()
            }
            override fun onPlacedTap(protocolId: String) {
                if (protocolId.startsWith("B")) {
                    viewModel.selectObstacle(protocolId)
                    showObstacleDetailsDialog(protocolId)
                }
            }

            override fun onPlacedDrag(protocolId: String, x: Int, y: Int) {
                viewModel.previewMovePlaced(protocolId, x, y)
            }

            override fun onPlacedDrop(protocolId: String, x: Int, y: Int) {
                viewModel.movePlaced(protocolId, x, y)
            }

            override fun onPlacedRemove(protocolId: String) {
                viewModel.removePlaced(protocolId)
            }

            override fun onRobotTap() {
                showRobotPoseDialog()
            }
        })

        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.state.collect { s ->
                    s.robot?.let {
                        arenaView.setRobotRect(it.x, it.y, it.robotX, it.robotY, it.robotDirection)
                    }
                    arenaView.setArena(s.arena)
                    arenaView.setPendingPreview(s.pendingPreview)
                    arenaView.setPendingActive(s.pendingObstacle != null)
                    arenaView.setDragPreview(s.dragPreview)
                }
            }
        }
    }

    private fun showObstacleDetailsDialog(protocolId: String){
        val dialogView = layoutInflater.inflate(R.layout.dialog_obstacle_details, null)

        val tabConfig = dialogView.findViewById<TextView>(R.id.tabConfig)
        val tabImage = dialogView.findViewById<TextView>(R.id.tabImage)

        val panelConfig = dialogView.findViewById<View>(R.id.panelConfig)
        val panelImage = dialogView.findViewById<View>(R.id.panelImage)

        val spFacing = dialogView.findViewById<Spinner>(R.id.spFacing)
        spFacing.adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, DirectionUtil.faces)

        val iv = dialogView.findViewById<android.widget.ImageView>(R.id.ivObstacleImage)
        val tvEmpty = dialogView.findViewById<TextView>(R.id.tvNoImage)

        fun switchToConfig() {
            panelConfig.visibility = View.VISIBLE
            panelImage.visibility = View.GONE
            tabConfig.isSelected = true
            tabImage.isSelected = false
        }

        fun switchToImage() {
            panelConfig.visibility = View.GONE
            panelImage.visibility = View.VISIBLE
            tabConfig.isSelected = false
            tabImage.isSelected = true

            val bytes = viewModel.state.value.obstacleImages[protocolId]
            if (bytes == null || bytes.isEmpty()) {
                iv.setImageDrawable(null)
                iv.visibility = View.GONE
                tvEmpty.visibility = View.VISIBLE
            } else {
                val bmp = decodeScaled(bytes, 900, 900)
                if (bmp != null) {
                    iv.setImageBitmap(bmp)
                    iv.visibility = View.VISIBLE
                    tvEmpty.visibility = View.GONE
                } else {
                    iv.setImageDrawable(null)
                    iv.visibility = View.GONE
                    tvEmpty.visibility = View.VISIBLE
                    tvEmpty.text = "Unable to decode image"
                }
            }
        }

        tabConfig.setOnClickListener { switchToConfig() }
        tabImage.setOnClickListener { switchToImage() }

        switchToConfig()

        AlertDialog.Builder(requireContext())
            .setTitle("Obstacle $protocolId")
            .setView(dialogView)
            .setPositiveButton("Save") { _, _ ->
                val facing = DirectionUtil.fromProtocolToken(spFacing.selectedItem.toString())
                viewModel.setPlacedFacing(protocolId, facing)
            }
            .setNegativeButton("Close", null)
            .show()
    }

    private fun showObstacleConfigDialog(obstacleId: Int) {
        viewModel.pickObstacleToConfigure(obstacleId)
        val dialogView = layoutInflater.inflate(R.layout.dialog_obstacle_config, null)

        val etX = dialogView.findViewById<EditText>(R.id.etX)
        val etY = dialogView.findViewById<EditText>(R.id.etY)
        val etWidth = dialogView.findViewById<EditText>(R.id.etWidth)
        val etHeight = dialogView.findViewById<EditText>(R.id.etHeight)
        val spFacing = dialogView.findViewById<Spinner>(R.id.spFacing)

        etWidth.setText("2")
        etHeight.setText("2")

        spFacing.adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_dropdown_item, DirectionUtil.faces)

        AlertDialog.Builder(requireContext())
            .setTitle("Configure Obstacle B$obstacleId")
            .setView(dialogView)
            .setPositiveButton("Confirm") { _, _ ->
                val xText = etX.text.toString().trim()
                val yText = etY.text.toString().trim()
                val w = etWidth.text.toString().toIntOrNull() ?: 1
                val h = etHeight.text.toString().toIntOrNull() ?: 1
                val facing = DirectionUtil.fromProtocolToken(spFacing.selectedItem.toString())

                val hasX = xText.isNotEmpty()
                val hasY = yText.isNotEmpty()

                viewModel.updatePendingConfig(w, h, facing)

                when {
                    hasX && hasY -> {
                        val x = xText.toIntOrNull()
                        val y = yText.toIntOrNull()
                        if(x == null || y == null) return@setPositiveButton
                        viewModel.placeObstacleDirect(obstacleId, x, y, w, h, facing)
                    }

                    else -> {}
                }
            }
            .setNegativeButton("Cancel") { _, _ ->
                viewModel.cancelPending()
            }
            .show()
    }

    private fun showRobotPoseDialog() {
        val dialogView = layoutInflater.inflate(R.layout.dialog_robot_pose, null)

        val blX = dialogView.findViewById<EditText>(R.id.blX)
        val blY = dialogView.findViewById<EditText>(R.id.blY)
        val etW = dialogView.findViewById<EditText>(R.id.etW)
        val etH = dialogView.findViewById<EditText>(R.id.etH)
        val spFacing = dialogView.findViewById<Spinner>(R.id.spFacing)

        spFacing.adapter = ArrayAdapter(
            requireContext(),
            android.R.layout.simple_spinner_dropdown_item,
            DirectionUtil.faces
        )

        val s0 = viewModel.state.value
        val r0 = s0.robot
        blX.setText((r0?.x ?: 1).toString())
        blY.setText((r0?.y ?: 1).toString())
        etW.setText((r0?.robotX ?: 3).toString())
        etH.setText((r0?.robotY ?: 3).toString())

        val faceIdx = when (r0?.robotDirection ?: RobotDirection.NORTH) {
            RobotDirection.NORTH -> 0
            RobotDirection.EAST -> 1
            RobotDirection.SOUTH -> 2
            RobotDirection.WEST -> 3
        }
        spFacing.setSelection(faceIdx)

        AlertDialog.Builder(requireContext())
            .setTitle("Set Robot Pose")
            .setView(dialogView)
            .setPositiveButton("OK") { _, _ ->
                val x = blX.text.toString().toIntOrNull() ?: 1
                val y = blY.text.toString().toIntOrNull() ?: 1
                val w = etW.text.toString().toIntOrNull() ?: 3
                val h = etH.text.toString().toIntOrNull() ?: 3

                val facing = when (spFacing.selectedItem as String) {
                    DirectionUtil.faces[0] -> RobotDirection.NORTH
                    DirectionUtil.faces[1] -> RobotDirection.EAST
                    DirectionUtil.faces[2] -> RobotDirection.SOUTH
                    else -> RobotDirection.WEST
                }

                viewModel.setRobotPose(x, y, w, h, facing, alsoSend = true)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun decodeScaled(bytes: ByteArray, reqW: Int, reqH: Int): android.graphics.Bitmap? {
        return try {
            val opts = android.graphics.BitmapFactory.Options().apply { inJustDecodeBounds = true }
            android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size, opts)

            opts.inSampleSize = calculateInSampleSize(opts, reqW, reqH)
            opts.inJustDecodeBounds = false

            android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size, opts)
        } catch (_: Exception) {
            null
        }
    }

    private fun calculateInSampleSize(opts: android.graphics.BitmapFactory.Options, reqW: Int, reqH: Int): Int {
        val (h, w) = opts.outHeight to opts.outWidth
        var inSample = 1
        while (h / inSample > reqH || w / inSample > reqW) inSample *= 2
        return inSample
    }
}

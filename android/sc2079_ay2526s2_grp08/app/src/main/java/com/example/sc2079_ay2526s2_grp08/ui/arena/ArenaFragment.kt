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
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.example.sc2079_ay2526s2_grp08.MainActivity
import com.example.sc2079_ay2526s2_grp08.R
import com.example.sc2079_ay2526s2_grp08.domain.*
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
        view.findViewById<Button>(R.id.btnBlock)?.setOnClickListener { showObstacleConfigDialog(null) }

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
                    showFaceDialog(protocolId)
                } else {}
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

    private fun showFaceDialog(protocolId: String) {
        val options = arrayOf("N", "E", "S", "W")

        AlertDialog.Builder(requireContext())
            .setTitle("Obstacle $protocolId facing")
            .setItems(options) { _, which ->
                val face = when (options[which]) {
                    "N" -> RobotDirection.NORTH
                    "E" -> RobotDirection.EAST
                    "S" -> RobotDirection.SOUTH
                    "W" -> RobotDirection.WEST
                    else -> RobotDirection.NORTH
                }
                viewModel.setPlacedFacing(protocolId, face)
            }

            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showObstacleConfigDialog(obstacleId: Int?) {
        viewModel.pickObstacleToConfigure(obstacleId)

        val dialogView = layoutInflater.inflate(R.layout.dialog_obstacle_config, null)

        val etWidth = dialogView.findViewById<EditText>(R.id.etWidth)
        val etHeight = dialogView.findViewById<EditText>(R.id.etHeight)
        val spFacing = dialogView.findViewById<Spinner>(R.id.spFacing)
        val tvFacingLabel = dialogView.findViewById<TextView>(R.id.tvFacingLabel)

        // defaults
        etWidth.setText("2")
        etHeight.setText("2")

        val isBlock = obstacleId == null
        if (isBlock) {
            tvFacingLabel.visibility = View.GONE
            spFacing.visibility = View.GONE
        } else {
            val faces = listOf("N", "E", "S", "W")
            spFacing.adapter = ArrayAdapter(
                requireContext(),
                android.R.layout.simple_spinner_dropdown_item,
                faces
            )
        }

        AlertDialog.Builder(requireContext())
            .setTitle(if (isBlock) "Configure Blockage" else "Configure Obstacle B$obstacleId")
            .setView(dialogView)
            .setPositiveButton("OK") { _, _ ->
                val w = etWidth.text.toString().toIntOrNull() ?: 1
                val h = etHeight.text.toString().toIntOrNull() ?: 1

                val facing =
                    if (isBlock) null
                    else when (spFacing.selectedItem as String) {
                        "N" -> RobotDirection.NORTH
                        "E" -> RobotDirection.EAST
                        "S" -> RobotDirection.SOUTH
                        else -> RobotDirection.WEST
                    }

                viewModel.updatePendingConfig(w, h, facing)
            }
            .setNegativeButton("Cancel") { _, _ ->
                viewModel.cancelPending()
            }
            .show()
    }
}

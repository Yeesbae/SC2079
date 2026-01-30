package com.example.sc2079_ay2526s2_grp08.ui.arena

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.example.sc2079_ay2526s2_grp08.MainActivity
import com.example.sc2079_ay2526s2_grp08.R
import com.example.sc2079_ay2526s2_grp08.domain.Facing
import com.example.sc2079_ay2526s2_grp08.domain.ObstacleState
import kotlinx.coroutines.launch

class ArenaFragment : Fragment() {

    private val viewModel by lazy { (requireActivity() as MainActivity).viewModel }

    private var selectedId = 1

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View = inflater.inflate(R.layout.fragment_arena, container, false)

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val arenaView = view.findViewById<ArenaView>(R.id.arenaView) ?: return
        val tvSelected = view.findViewById<TextView>(R.id.tvSelected) ?: return

        fun setSelected(id: Int) {
            selectedId = id
            tvSelected.text = "Obstacle: $id"
        }

        view.findViewById<Button>(R.id.btnObs1)?.setOnClickListener { setSelected(1) }
        view.findViewById<Button>(R.id.btnObs2)?.setOnClickListener { setSelected(2) }
        view.findViewById<Button>(R.id.btnObs3)?.setOnClickListener { setSelected(3) }
        view.findViewById<Button>(R.id.btnObs4)?.setOnClickListener { setSelected(4) }
        view.findViewById<Button>(R.id.btnObs5)?.setOnClickListener { setSelected(5) }
        view.findViewById<Button>(R.id.btnObs6)?.setOnClickListener { setSelected(6) }
        view.findViewById<Button>(R.id.btnObs7)?.setOnClickListener { setSelected(7) }
        view.findViewById<Button>(R.id.btnObs8)?.setOnClickListener { setSelected(8) }

        setSelected(1)

        arenaView.setListener(object : ArenaView.Listener {
            override fun onCellTap(x: Int, y: Int) {
                viewModel.placeOrMoveObstacle(selectedId, x, y)
            }

            override fun onObstacleTap(obstacleId: Int) {
                showFaceDialog(obstacleId)
            }

            override fun onObstacleDrag(obstacleId: Int, x: Int, y: Int) {
                viewModel.placeOrMoveObstacle(obstacleId, x, y)
            }

            override fun onObstacleRemove(obstacleId: Int) {
                viewModel.removeObstacle(obstacleId)
            }
        })

        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.state.collect { s ->
                    s.robot?.let { arenaView.setRobotPosition(it.x, it.y) }
                    arenaView.setObstacleBlocks(s.obstacleBlocks)
                }
            }
        }
    }

    private fun showFaceDialog(obstacleId: Int) {
        val options = arrayOf("N", "E", "S", "W")

        AlertDialog.Builder(requireContext())
            .setTitle("Obstacle $obstacleId facing")
            .setItems(options) { _, which ->
                val face = when (options[which]) {
                    "N" -> Facing.N
                    "E" -> Facing.E
                    "S" -> Facing.S
                    "W" -> Facing.W
                    else -> null
                }
                viewModel.setObstacleFacing(obstacleId, face)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
}

package com.example.sc2079_ay2526s2_grp08.ui.controller

import android.os.Bundle
import android.view.View
import android.widget.Button
import androidx.fragment.app.Fragment
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.example.sc2079_ay2526s2_grp08.MainActivity
import com.example.sc2079_ay2526s2_grp08.R
import com.example.sc2079_ay2526s2_grp08.ui.arena.ArenaView
import kotlinx.coroutines.launch

class ControllerFragment : Fragment(R.layout.fragment_controller) {

    private val viewModel by lazy { (requireActivity() as MainActivity).viewModel }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val arenaView = view.findViewById<ArenaView>(R.id.arenaView) ?: return

        // Observe shared robot state and render it
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.state.collect { s ->
                    s.robot?.let { arenaView.setRobotPosition(it.x, it.y) }
                }
            }
        }

        // Buttons send commands via ViewModel (single source of truth)
        view.findViewById<Button>(R.id.btnForward)?.setOnClickListener {
            viewModel.sendMoveForward()
        }

        view.findViewById<Button>(R.id.btnBack)?.setOnClickListener {
            viewModel.sendMoveBackward()
        }

        view.findViewById<Button>(R.id.btnLeft)?.setOnClickListener {
            viewModel.sendTurnLeft()
        }

        view.findViewById<Button>(R.id.btnRight)?.setOnClickListener {
            viewModel.sendTurnRight()
        }

        view.findViewById<Button>(R.id.btnStop)?.setOnClickListener {
            viewModel.sendRaw("STOP")
        }
    }
}

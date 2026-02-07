package com.example.sc2079_ay2526s2_grp08.viewmodel.reducers

import com.example.sc2079_ay2526s2_grp08.domain.AppState
import com.example.sc2079_ay2526s2_grp08.domain.LogEntry

/**
 * Pure log buffer updates (capping, append, clear).
 */
object LogReducer {
    private const val MAX_LOG = 300

    fun append(state: AppState, kind: LogEntry.Kind, text: String): AppState {
        val next = state.log + LogEntry(kind, text)
        val capped = if (next.size > MAX_LOG) next.takeLast(MAX_LOG) else next
        return state.copy(log = capped)
    }

    fun clear(state: AppState): AppState = state.copy(log = emptyList())
}

package com.example.sc2079_ay2526s2_grp08.protocol

object ProtocolEncoder {
    fun encode(cmd: Outgoing): String = when (cmd) {
        is Outgoing.Raw -> cmd.line.trim()
        is Outgoing.Move -> cmd.code.trim()
    }
}
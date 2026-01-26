package com.example.sc2079_ay2526s2_grp08.bluetooth

import android.bluetooth.BluetoothSocket
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.ByteArrayOutputStream
import java.util.ArrayDeque
import java.util.concurrent.atomic.AtomicBoolean

internal class BluetoothCommunicationService(
    private val echoWindow: Int = BluetoothConfig.ECHO_WINDOW,
    private val readBufSize: Int = BluetoothConfig.READ_BUF_SIZE,
) {
    private val writeLock = Any()

    private var socket: BluetoothSocket? = null
    private var inStream: BufferedInputStream? = null
    private var outStream: BufferedOutputStream? = null

    private var readerThread: Thread? = null
    private val running = AtomicBoolean(false)

    private val echoTracker = EchoTracker(echoWindow)
    private val lineBuilder = LineBuilder()

    var onLine: ((String, isEcho: Boolean) -> Unit)? = null
    var onSessionEnded: ((BluetoothManager.DisconnectReason, String?) -> Unit)? = null
    var onSendError: ((String) -> Unit)? = null

    fun isActive(): Boolean = running.get() && socket != null

    fun startSession(s: BluetoothSocket) {
        closeSessionInternal(null, null)

        socket = s
        inStream = BufferedInputStream(s.inputStream)
        outStream = BufferedOutputStream(s.outputStream)

        running.set(true)
        startReaderLoop()
    }

    fun sendLine(lineNoNewline: String): Boolean {
        val os = outStream ?: return false
        if (!running.get() || socket == null) return false

        val toSend = lineNoNewline.trim()
        echoTracker.rememberSent(toSend)

        Thread {
            try {
                synchronized(writeLock) {
                    os.write((toSend + "\n").toByteArray(Charsets.UTF_8))
                    os.flush()
                }
            } catch (e: Exception) {
                onSendError?.invoke(e.message ?: e.javaClass.simpleName)
                // Treat as session failure (remote may be gone)
                closeSessionInternal(BluetoothManager.DisconnectReason.ERROR, "Send failed: ${e.message ?: e.javaClass.simpleName}")
            }
        }.start()

        return true
    }

    fun closeSession(reason: BluetoothManager.DisconnectReason, msg: String?) {
        closeSessionInternal(reason, msg)
    }

    fun resetParsers() {
        echoTracker.reset()
        lineBuilder.reset()
    }

    private fun startReaderLoop() {
        readerThread = Thread {
            val input = inStream ?: return@Thread
            val buf = ByteArray(readBufSize)

            try {
                while (running.get()) {
                    val n = input.read(buf)
                    if (n <= 0) {
                        closeSessionInternal(BluetoothManager.DisconnectReason.REMOTE, "Remote closed connection")
                        break
                    }

                    val hadDelimiter = lineBuilder.append(buf, n) { line ->
                        val isEcho = echoTracker.isEcho(line)
                        onLine?.invoke(line, isEcho)
                    }

                    if (!hadDelimiter && lineBuilder.hasPending()) {
                        try { Thread.sleep(50) } catch (_: Exception) {}
                        if (lineBuilder.hasPending()) {
                            lineBuilder.flush { line ->
                                val isEcho = echoTracker.isEcho(line)
                                onLine?.invoke(line, isEcho)
                            }
                        }
                    }

                }
            } catch (e: Exception) {
                val msg = e.message ?: e.javaClass.simpleName
                val reason =
                    if (msg.contains("read return: -1", ignoreCase = true) ||
                        msg.contains("socket closed", ignoreCase = true)
                    ) BluetoothManager.DisconnectReason.REMOTE
                    else BluetoothManager.DisconnectReason.ERROR

                closeSessionInternal(reason, msg)
            }
        }.also { it.start() }
    }

    @Synchronized
    private fun closeSessionInternal(reason: BluetoothManager.DisconnectReason?, msg: String?) {
        if (!running.get() && socket == null) return

        running.set(false)

        val t = readerThread
        readerThread = null
        try { t?.interrupt() } catch (_: Exception) {}

        try { inStream?.close() } catch (_: Exception) {}
        try { outStream?.close() } catch (_: Exception) {}
        try { socket?.close() } catch (_: Exception) {}

        inStream = null
        outStream = null
        socket = null

        if (t != null && t != Thread.currentThread()) {
            try { t.join(300) } catch (_: Exception) {}
        }

        try { lineBuilder.flush { line -> onLine?.invoke(line, false) } } catch (_: Exception) {}

        echoTracker.reset()
        lineBuilder.reset()

        if (reason != null) onSessionEnded?.invoke(reason, msg)
    }

    private class EchoTracker(private val windowSize: Int) {
        private val q = ArrayDeque<String>(windowSize)

        fun rememberSent(line: String) {
            val trimmed = line.trim()
            synchronized(q) {
                if (q.size >= windowSize) q.removeFirst()
                q.addLast(trimmed)
            }
        }

        fun isEcho(line: String): Boolean {
            val trimmed = line.trim()
            synchronized(q) {
                val idx = q.indexOfFirst { it == trimmed }
                if (idx >= 0) {
                    repeat(idx + 1) { q.removeFirst() }
                    return true
                }
            }
            return false
        }

        fun reset() = synchronized(q) { q.clear() }
    }

    private class LineBuilder {
        private val buf = ByteArrayOutputStream()

        fun append(bytes: ByteArray, n: Int, onLine: (String) -> Unit): Boolean {
            var emitted = false
            for (i in 0 until n) {
                when (val b = bytes[i]) {
                    '\n'.code.toByte(), '\r'.code.toByte() -> {
                        emitted = true
                        flush(onLine)
                    }
                    else -> buf.write(b.toInt())
                }
            }
            return emitted
        }

        fun flush(onLine: (String) -> Unit) {
            val line = buf.toString(Charsets.UTF_8.name()).trim()
            buf.reset()
            if (line.isNotEmpty()) onLine(line)
        }

        fun hasPending(): Boolean = buf.size() > 0

        fun reset() = buf.reset()
    }

}
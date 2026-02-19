package com.example.sc2079_ay2526s2_grp08.bluetooth

import android.bluetooth.BluetoothSocket
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.ByteArrayOutputStream
import java.util.ArrayDeque
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.atomic.AtomicBoolean

internal class BluetoothCommunicationService(
    private val echoWindow: Int = BluetoothConfig.ECHO_WINDOW,
    private val readBufSize: Int = BluetoothConfig.READ_BUF_SIZE,
) {
    private val writeLock = Any()

    private var socket: BluetoothSocket? = null
    private var inStream: BufferedInputStream? = null
    private var outStream: BufferedOutputStream? = null

    private var writeQueue = LinkedBlockingQueue<String>(256)
    private var writerThread: Thread? = null
    private var readerThread: Thread? = null
    private val running = AtomicBoolean(false)

    private val echoTracker = EchoTracker(echoWindow)
    private val lineBuilder = LineBuilder()

    @Volatile private var expectingImageBytes: Int = 0
    private var imgObstacleId: String? = null
    private var imgTargetId: String? = null
    private var imgFace: String? = null
    private var imgBuf: ByteArray? = null
    private var imgOff: Int = 0

    var onLine: ((String, isEcho: Boolean) -> Unit)? = null
    var onSessionEnded: ((BluetoothManager.DisconnectReason, String?) -> Unit)? = null
    var onSendError: ((String) -> Unit)? = null
    var onImage: ((obstacleId: String, targetId: String, face: String?, bytes: ByteArray) -> Unit)? = null

    fun isActive(): Boolean = running.get() && socket != null

    fun startSession(s: BluetoothSocket) {
        closeSessionInternal(null, null)

        socket = s
        inStream = BufferedInputStream(s.inputStream)
        outStream = BufferedOutputStream(s.outputStream)

        writeQueue.clear()

        running.set(true)
        startWriterLoop()
        startReaderLoop()
    }

    fun sendLine(lineNoNewline: String): Boolean {
        if (!running.get() || socket == null) return false

        val toSend = lineNoNewline.trimEnd('\r','\n',' ')
        if (toSend.isEmpty()) return true

        echoTracker.rememberSent(toSend)

        val ok = writeQueue.offer(toSend)
        if (!ok){
            onSendError?.invoke("Send Queue Full")
            closeSessionInternal(
                BluetoothManager.DisconnectReason.ERROR,
                "Send Queue Fail"
            )
        }
        return ok
    }

    fun closeSession(reason: BluetoothManager.DisconnectReason, msg: String?) {
        closeSessionInternal(reason, msg)
    }

    fun resetParsers() {
        echoTracker.reset()
        lineBuilder.reset()
    }

    private fun startWriterLoop() {
        writerThread = Thread {
            while (running.get()){
                val os = outStream ?: break
                try {
                    val line = writeQueue.take()
                    synchronized(writeLock) {
                        os.write((line + BluetoothConfig.LINE_ENDING).toByteArray(Charsets.UTF_8))
                        os.flush()
                }
            } catch (ie: InterruptedException) {
                break
            } catch (e: Exception) {
                    val msg = e.message ?: e.javaClass.simpleName
                    onSendError?.invoke(msg)
                    closeSessionInternal(
                        BluetoothManager.DisconnectReason.ERROR,
                        "Send failed: $msg")
                    break
                }
            }
        }.also { it.start() }
    }

    private fun startReaderLoop() {
        readerThread = Thread {
            val input = inStream ?: return@Thread
            val buf = ByteArray(readBufSize)

            try {
                while (running.get()) {
                    val n = input.read(buf)
                    if (n <= 0) {
                        closeSessionInternal(
                            BluetoothManager.DisconnectReason.REMOTE,
                            "Remote closed connection"
                        )
                        break
                    }

                    var offset = 0

                    while (offset < n) {
                        if (expectingImageBytes > 0) {
                            val take = minOf(expectingImageBytes, n - offset)

                            val out = imgBuf ?: ByteArray(expectingImageBytes).also {
                                imgBuf = it
                            }

                            System.arraycopy(buf, offset, out, imgOff, take)

                            imgOff += take
                            expectingImageBytes -= take
                            offset += take

                            if (expectingImageBytes == 0) {
                                val obstacleId = imgObstacleId
                                val targetId = imgTargetId
                                val face = imgFace
                                val bytes = imgBuf

                                imgObstacleId = null
                                imgTargetId = null
                                imgFace = null
                                imgBuf = null
                                imgOff = 0

                                if (obstacleId != null && targetId != null && bytes != null) {
                                    onImage?.invoke(obstacleId, targetId, face, bytes)
                                }
                            }

                            continue
                        }

                        val b = buf[offset]

                        if (b == '\n'.code.toByte() || b == '\r'.code.toByte()) {
                            val line = lineBuilder.consumeLine()

                            if (line != null) {
                                val hdr = parseImageHeader(line)
                                if (hdr != null) {
                                    expectingImageBytes = hdr.len
                                    imgObstacleId = hdr.obstacleId
                                    imgTargetId = hdr.targetId
                                    imgFace = hdr.face
                                    imgBuf = ByteArray(hdr.len)
                                    imgOff = 0
                                } else {
                                    val isEcho = echoTracker.isEcho(line)
                                    onLine?.invoke(line, isEcho)
                                }
                            }
                        } else {
                            lineBuilder.appendByte(b)
                        }
                        offset++
                    }
                }

            } catch (e: Exception) {
                val msg = e.message ?: e.javaClass.simpleName
                val reason =
                    if (msg.contains("read return: -1", true) ||
                        msg.contains("socket closed", true)
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

        val wt = writerThread
        writerThread = null
        try { wt?.interrupt() } catch (_: Exception) {}
        writeQueue.clear()

        val rt = readerThread
        readerThread = null
        try { rt?.interrupt() } catch (_: Exception) {}

        try { inStream?.close() } catch (_: Exception) {}
        try { outStream?.close() } catch (_: Exception) {}
        try { socket?.close() } catch (_: Exception) {}

        inStream = null
        outStream = null
        socket = null

        if (wt != null && wt != Thread.currentThread()) {
            try { wt.join(300) } catch (_: Exception) {}
        }
        if (rt != null && rt != Thread.currentThread()) {
            try { rt.join(300) } catch (_: Exception) {}
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

    //bytes stream detection outside of protocolparser as it is not a linebreak
    private fun parseImageHeader(line: String): ImageHeader? {
        val parts = line.split(",").map { it.trim() }
        if (parts.size < 6) return null
        if (parts[0].uppercase() != "T") return null

        val obstacleId = parts[1]
        val targetId = parts[2]
        val face = parts[3].takeIf { it != "-" && it.isNotBlank() }

        val typeMarker = parts[4]
        val len = parts[5].toIntOrNull() ?: return null

        if (len <= 0 || len > 2_000_000) return null

        return ImageHeader(obstacleId, targetId, face, typeMarker, len)
    }

    private data class ImageHeader(val obstacleId: String, val targetId: String, val face: String?, val typeMarker: String?, val len: Int)

    private class LineBuilder {
        private val buf = ByteArrayOutputStream()

        fun appendByte(b: Byte){
            buf.write(b.toInt())
        }

        fun consumeLine(): String? {
            val line = buf.toString(Charsets.UTF_8.name()).trim()
            buf.reset()
            return if (line.isNotEmpty()) line else null
        }

        fun flush(onLine: (String) -> Unit) {
            val line = buf.toString(Charsets.UTF_8.name()).trim()
            buf.reset()
            val cleaned = line.trim()
            if (cleaned.isNotEmpty()) onLine(cleaned)
        }

        fun reset() = buf.reset()
    }

}
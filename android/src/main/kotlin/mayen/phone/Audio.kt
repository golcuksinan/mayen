package mayen.phone

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.media.audiofx.AcousticEchoCanceler
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

private const val TAG = "mayen.audio"

// Mikrofondan okunan parça: VAD'ın ve ağın gördüğü en küçük gecikme (clients/mic.py ile aynı)
private const val BLOCK_S = 0.02

// Sessizlikten sonra çalmadan önce biriktirilen ses: ağın titremesini karşılar. Tailnet'te
// cevabın ortasında 170 ms'ye varan, art arda gelen boşluklar ölçüldü (18 Ekim 2026).
private const val HOLD_MS = 300
private const val POLL_MS = 20L

// Kanalın biçimi: 16 bit, tek kanal (ports/channels.py)
private const val PCM = AudioFormat.ENCODING_PCM_16BIT

// Kulaklık, varsa görüşme aygıtıdır; yoksa hoparlör (görüşme kipinin varsayılanı ahizedir)
private val PREFERRED = listOf(
    AudioDeviceInfo.TYPE_BLE_HEADSET,
    AudioDeviceInfo.TYPE_BLUETOOTH_SCO,
    AudioDeviceInfo.TYPE_WIRED_HEADSET,
    AudioDeviceInfo.TYPE_USB_HEADSET,
    AudioDeviceInfo.TYPE_BUILTIN_SPEAKER,
)

/** Sesin alındığı mikrofon; çekirdeğe bildirilir, sözün kaydının yanına yazılır. */
data class Input(val source: String, val name: String)

fun input(device: AudioDeviceInfo?): Input {
    val source = when (device?.type) {
        null -> "unknown"
        AudioDeviceInfo.TYPE_BUILTIN_MIC -> "builtin_mic"
        AudioDeviceInfo.TYPE_WIRED_HEADSET -> "wired_headset"
        AudioDeviceInfo.TYPE_USB_HEADSET, AudioDeviceInfo.TYPE_USB_DEVICE -> "usb_headset"
        AudioDeviceInfo.TYPE_BLUETOOTH_SCO -> "bluetooth_headset"
        AudioDeviceInfo.TYPE_BLE_HEADSET -> "ble_headset"
        else -> "type_${device.type}"
    }
    return Input(source, device?.productName?.toString().orEmpty())
}

// Telefonun ses yolu: mikrofon çekirdeğe, çekirdeğin sesi hoparlöre ya da kulaklığa. Ses
// görüşme kipindedir: kulaklığın mikrofonuna Android'de yalnızca görüşmeyle ulaşılır. İki yön
// de hep açıktır; Mayen konuşurken de dinlenir (söz kesme, §6).
//
// Hoparlörde mikrofon görüşme kaynağıdır (VOICE_COMMUNICATION): yankı giderici çalan sesi
// çıkarır, Mayen kendi sesini duymaz. Kulaklıkta yankı yoktur, çalan ses mikrofona sızmaz;
// mikrofon ses tanıma kaynağıdır (VOICE_RECOGNITION): telefonun görüşme işlemesinden geçmez,
// konuşma bandı daha güçlü gelir (ölçüm, 18 Ekim 2026). Kulaklık takılıp çıkınca mikrofon
// yeni kaynakla yeniden açılır.
class Audio(
    context: Context,
    private val inputRate: Int,
    private val outputRate: Int,
    private val send: (ByteArray) -> Unit,
    private val routed: (Input) -> Unit,
) {
    private val manager = context.getSystemService(AudioManager::class.java)
    private val main = Handler(Looper.getMainLooper())
    private val playback = LinkedBlockingQueue<ByteArray>()
    private lateinit var track: AudioTrack
    private var player: Thread? = null
    private var microphone: Microphone? = null // kilitle: hizmetin ve ana iş parçacığının
    private var last: Input? = null

    @Volatile
    private var running = false

    // Kulaklık takılınca ya da çıkınca görüşme aygıtı ve mikrofonun kaynağı yeniden seçilir
    private val devices = object : AudioDeviceCallback() {
        override fun onAudioDevicesAdded(added: Array<out AudioDeviceInfo>) = choose()
        override fun onAudioDevicesRemoved(removed: Array<out AudioDeviceInfo>) = choose()
    }

    fun start() {
        manager.mode = AudioManager.MODE_IN_COMMUNICATION
        track = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build(),
            )
            .setAudioFormat(format(outputRate, AudioFormat.CHANNEL_OUT_MONO))
            .setTransferMode(AudioTrack.MODE_STREAM)
            .setBufferSizeInBytes(AudioTrack.getMinBufferSize(outputRate, AudioFormat.CHANNEL_OUT_MONO, PCM) * 2)
            .build()
        running = true
        track.play()
        player = Thread(::play, "mayen-play").apply { start() }
        choose()
        manager.registerAudioDeviceCallback(devices, main)
    }

    fun play(pcm: ByteArray) {
        playback.put(pcm)
    }

    fun stop() {
        manager.unregisterAudioDeviceCallback(devices)
        running = false
        synchronized(this) {
            microphone?.close()
            microphone = null
        }
        player?.join()
        track.stop()
        track.release()
        manager.clearCommunicationDevice()
        manager.mode = AudioManager.MODE_NORMAL
    }

    // Çekirdek sesi çalınma hızında yollar; ağda gecikip gelen bir parça çalan sesi keserdi.
    // Kart boşken gelen parçalar biriktirilir, `HOLD_MS` kadar ses birikince ya da o kadar
    // süre geçince (kısa bir cevabın tamamı birikimi doldurmayabilir) çalınır.
    private fun play() {
        val held = ArrayList<ByteArray>()
        var heldBytes = 0
        var since = 0L
        var written = 0L // karta yazılan kare
        val enough = outputRate * 2 * HOLD_MS / 1000

        fun release() {
            held.forEach {
                track.write(it, 0, it.size)
                written += it.size / 2
            }
            held.clear()
            heldBytes = 0
        }

        while (running) {
            val pcm = playback.poll(POLL_MS, TimeUnit.MILLISECONDS)
            if (pcm == null) {
                if (held.isNotEmpty() && SystemClock.elapsedRealtime() - since >= HOLD_MS) release()
                continue
            }
            // Kartta çalınmayı bekleyen ses varsa parça arkasına eklenir
            if (written - track.playbackHeadPosition.toLong().and(0xFFFFFFFFL) > 0 && held.isEmpty()) {
                track.write(pcm, 0, pcm.size)
                written += pcm.size / 2
                continue
            }
            if (held.isEmpty()) since = SystemClock.elapsedRealtime()
            held.add(pcm)
            heldBytes += pcm.size
            if (heldBytes >= enough) release()
        }
    }

    private fun choose() {
        val available = manager.availableCommunicationDevices
        val device = PREFERRED.firstNotNullOfOrNull { type -> available.firstOrNull { it.type == type } }
        if (device != null && manager.communicationDevice?.id != device.id) {
            manager.setCommunicationDevice(device)
        }
        val source = if (device == null || device.type == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER) {
            MediaRecorder.AudioSource.VOICE_COMMUNICATION
        } else {
            MediaRecorder.AudioSource.VOICE_RECOGNITION
        }
        synchronized(this) {
            if (!running || microphone?.source == source) return
            microphone?.close()
            microphone = Microphone(source)
        }
    }

    private fun report() {
        val record = synchronized(this) { microphone?.record } ?: return
        val now = input(record.routedDevice)
        if (now == last) return
        last = now
        Log.i(TAG, "input: ${now.source} (${now.name})")
        routed(now)
    }

    private fun format(rate: Int, channel: Int) = AudioFormat.Builder()
        .setEncoding(PCM)
        .setSampleRate(rate)
        .setChannelMask(channel)
        .build()

    @Suppress("MissingPermission") // izin hizmet başlamadan alınır (MainActivity)
    private inner class Microphone(val source: Int) {
        private val block = (inputRate * BLOCK_S).toInt() * 2
        val record: AudioRecord = AudioRecord.Builder()
            .setAudioSource(source)
            .setAudioFormat(format(inputRate, AudioFormat.CHANNEL_IN_MONO))
            .setBufferSizeInBytes(maxOf(block * 4, AudioRecord.getMinBufferSize(inputRate, AudioFormat.CHANNEL_IN_MONO, PCM)))
            .build()
        private val echo = if (source == MediaRecorder.AudioSource.VOICE_COMMUNICATION && AcousticEchoCanceler.isAvailable()) {
            AcousticEchoCanceler.create(record.audioSessionId)?.apply { enabled = true }
        } else {
            null
        }

        @Volatile
        private var open = true
        private val reader = Thread(::capture, "mayen-mic")

        init {
            val name = if (source == MediaRecorder.AudioSource.VOICE_COMMUNICATION) "voice_communication" else "voice_recognition"
            Log.i(TAG, "microphone source: $name")
            record.addOnRoutingChangedListener({ report() }, main)
            record.startRecording()
            reader.start()
            main.post(::report)
        }

        fun close() {
            open = false
            reader.join()
            record.stop()
            record.release()
            echo?.release()
        }

        private fun capture() {
            val buffer = ByteArray(block)
            while (open) {
                val n = record.read(buffer, 0, block)
                if (n > 0) send(buffer.copyOf(n))
            }
        }
    }
}

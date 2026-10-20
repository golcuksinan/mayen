package mayen.phone

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import okio.ByteString.Companion.toByteString
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import java.util.concurrent.Executors

private const val TAG = "mayen.link"
private const val VOICE_SCHEMA_VERSION = 2 // ports/channels.py
private const val RETRY_MS = 2000L

// Çekirdeğin sesli kanalı (§13, ports/channels.py): selamı alır, yeteneklerini bildirir,
// mikrofonu sürekli akıtır, gelen sesi çalar. Selamdan sonraki metin mesajları ya cihaz
// komutudur (ports/devices.py) ya ekran mesajı (ports/screen.py). Komut kendi iş
// parçacığında yürür: uzun bir komut sesi bekletmez. Bozuk bir mesaj istemciyi öldürmez;
// bağlantı koparsa yeniden kurulur. Kimliğini beyan etmez: çekirdek onu Tailscale'den okur.
class Link(private val context: Context, private val url: String) {
    private val http = OkHttpClient()
    private val main = Handler(Looper.getMainLooper())
    private val commands = Executors.newCachedThreadPool()
    private val media = Media(context)

    @Volatile
    private var stopped = false
    private var socket: WebSocket? = null

    fun start() = connect()

    fun stop() {
        stopped = true
        main.removeCallbacksAndMessages(null)
        socket?.close(1000, null)
        commands.shutdownNow()
    }

    private fun connect() {
        if (stopped) return
        Screen.connection("connecting")
        socket = http.newWebSocket(Request.Builder().url(url).build(), Listener())
    }

    private inner class Listener : WebSocketListener() {
        private var audio: Audio? = null

        override fun onMessage(webSocket: WebSocket, text: String) {
            if (audio == null) {
                hello(webSocket, text)
                return
            }
            val message = try {
                JSONObject(text)
            } catch (e: JSONException) {
                Log.w(TAG, "dropped a message that is not JSON: ${text.take(40)}")
                return
            }
            if (message.optString("type") != "command") {
                Screen.message(text)
                return
            }
            commands.execute {
                respond(message)?.let(webSocket::send)
            }
        }

        override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
            if (bytes.size % 2 != 0) {
                Log.w(TAG, "dropped a message that is not PCM")
                return
            }
            audio?.play(bytes.toByteArray())
        }

        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
            webSocket.close(1000, null)
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) = end("closed: $code $reason")

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) = end("$t")

        private fun hello(webSocket: WebSocket, text: String) {
            val (input, output) = try {
                val hello = JSONObject(text)
                val version = hello.getInt("schema_version")
                require(version == VOICE_SCHEMA_VERSION) {
                    "schema_version $version, expected $VOICE_SCHEMA_VERSION"
                }
                hello.getInt("input_sample_rate") to hello.getInt("output_sample_rate")
            } catch (e: Exception) {
                Log.e(TAG, "malformed hello: $e") // istemci çalışmaya başlamaz
                webSocket.close(1002, "malformed hello")
                return
            }
            val capabilities = JSONArray().apply { if (media.available()) put("media") }
            Log.i(TAG, "capabilities: $capabilities")
            webSocket.send(JSONObject().put("type", "capabilities").put("capabilities", capabilities).toString())
            audio = Audio(
                context,
                input,
                output,
                send = { webSocket.send(it.toByteString()) },
                routed = { webSocket.send(audioInput(it)) },
            ).also(Audio::start)
            Screen.connection("live")
        }

        private fun end(why: String) {
            Log.i(TAG, "connection ended: $why")
            audio?.stop()
            audio = null
            Screen.connection("lost")
            main.postDelayed(::connect, RETRY_MS)
        }
    }

    // Tanınmayan bir yetenek ya da eylem: çekirdek beklemesin, yapılamadığını bilsin
    private fun respond(command: JSONObject): String? {
        val id = command.optString("id").ifEmpty { return null }
        val result = try {
            if (command.optString("capability") != "media" || !media.available()) {
                Result("unsupported", JSONObject(), "no such capability")
            } else {
                val action = command.optString("action")
                media.handle(action, command.optJSONObject("args") ?: JSONObject())
                    ?: Result("unsupported", JSONObject(), "unknown action '$action'")
            }
        } catch (e: RuntimeException) {
            Result("error", JSONObject(), e.message ?: e.javaClass.simpleName)
        }
        return JSONObject()
            .put("type", "command_result")
            .put("id", id)
            .put("status", result.status)
            .put("data", result.data)
            .apply { result.error?.let { put("error", it) } }
            .toString()
    }

    private fun audioInput(input: Input) = JSONObject()
        .put("type", "audio_input")
        .put("source", input.source)
        .put("name", input.name)
        .toString()
}

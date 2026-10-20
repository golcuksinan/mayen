package mayen.phone

import android.app.NotificationManager
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.SystemClock
import android.service.notification.NotificationListenerService
import org.json.JSONArray
import org.json.JSONObject

// Etkinin görülmesi beklenen süre (clients/desktop.py ile aynı)
private const val EFFECT_WAIT_MS = 3000L
private const val POLL_MS = 50L

private val UNSEEN = mapOf(
    "play" to "the player is not playing",
    "pause" to "the player is still playing",
    "toggle" to "the player did not change",
    "next" to "the track did not change",
    "previous" to "the track did not change",
)

/** Medya oturumlarını görmenin tek yolu bildirim erişimidir; hizmetin kendisi bir şey yapmaz. */
class MediaAccess : NotificationListenerService()

private data class PlayerState(val status: String, val title: String?, val position: Long?)

// Medya yeteneği (§9.7, skills/media.py): telefonun medya oturumları. Davranışı masaüstünün
// `Media`'sıyla aynıdır: oynatıcı verilmezse çalan, çalan yoksa tek olan; ok yalnızca etki
// görülünce döner.
class Media(private val context: Context) {
    private val component = ComponentName(context, MediaAccess::class.java)
    private val sessions = context.getSystemService(MediaSessionManager::class.java)

    fun available(): Boolean =
        context.getSystemService(NotificationManager::class.java)
            .isNotificationListenerAccessGranted(component)

    /** Komutun sonucu, `data` ve `error` ile; `null` bu yeteneğin tanımadığı eylemdir. */
    fun handle(action: String, args: JSONObject): Result? {
        if (action != "status" && action !in UNSEEN) return null
        val players = players()
        if (action == "status") {
            val list = JSONArray()
            players.forEach { list.put(describe(it).apply { track(it).forEach { (k, v) -> put(k, v) } }) }
            return Result.ok(JSONObject().put("players", list))
        }
        val listed = JSONObject().put("players", JSONArray(players.map(::describe)))
        val wanted = args.optString("player").ifEmpty { null }
        val chosen = if (wanted != null) {
            players.filter { it.packageName == wanted }.ifEmpty {
                return Result.error("no player with id '$wanted'", listed)
            }
        } else {
            players.filter { status(it) == "playing" }.ifEmpty { players }
        }
        if (chosen.isEmpty()) return Result.error("no media player is open")
        if (chosen.size > 1) return Result.error("several players; say which one", listed)
        val player = chosen.single()
        val before = state(player)
        val controls = player.transportControls
        when (action) {
            "play" -> controls.play()
            "pause" -> controls.pause()
            "toggle" -> if (before.status == "playing") controls.pause() else controls.play()
            "next" -> controls.skipToNext()
            "previous" -> controls.skipToPrevious()
        }
        var after = state(player)
        val deadline = SystemClock.elapsedRealtime() + EFFECT_WAIT_MS
        while (!played(action, before, after) && SystemClock.elapsedRealtime() < deadline) {
            Thread.sleep(POLL_MS)
            after = state(player)
        }
        val data = JSONObject()
            .put("player", label(player.packageName))
            .put("id", player.packageName)
        track(player).forEach { (k, v) -> data.put(k, v) }
        if (!played(action, before, after)) return Result.error(UNSEEN.getValue(action), data)
        return Result.ok(data)
    }

    // Bir uygulama birden çok oturum tutabilir (PipePipe: ana, arka plan, açılır oynatıcı) ama
    // kişi için oynatıcı uygulamadır. Oturumlar en son etkin olandan başlar: her uygulamanın
    // ilki onun oynatıcısıdır.
    private fun players(): List<MediaController> =
        sessions.getActiveSessions(component).distinctBy { it.packageName }

    private fun describe(player: MediaController) = JSONObject()
        .put("id", player.packageName)
        .put("name", label(player.packageName))
        .put("status", status(player))

    // Şarkı ve sanatçı; adres verilmez: gereksiz, kişisel olabilir
    private fun track(player: MediaController): Map<String, String> {
        val metadata = player.metadata ?: return emptyMap()
        return listOfNotNull(
            metadata.getString(MediaMetadata.METADATA_KEY_TITLE)?.let { "title" to it },
            metadata.getString(MediaMetadata.METADATA_KEY_ARTIST)?.let { "artist" to it },
        ).toMap()
    }

    private fun status(player: MediaController) = when (player.playbackState?.state) {
        PlaybackState.STATE_PLAYING, PlaybackState.STATE_BUFFERING -> "playing"
        PlaybackState.STATE_PAUSED -> "paused"
        else -> "stopped"
    }

    private fun state(player: MediaController): PlayerState {
        val playback = player.playbackState
        // Konum son güncellemeden bu yana çalma hızıyla ilerlemiştir
        val position = playback?.takeIf { it.position >= 0 }?.let {
            if (it.state != PlaybackState.STATE_PLAYING) return@let it.position
            it.position + ((SystemClock.elapsedRealtime() - it.lastPositionUpdateTime) * it.playbackSpeed).toLong()
        }
        return PlayerState(status(player), player.metadata?.getString(MediaMetadata.METADATA_KEY_TITLE), position)
    }

    private fun played(action: String, before: PlayerState, now: PlayerState): Boolean = when (action) {
        "play" -> now.status == "playing"
        "pause" -> now.status != "playing"
        "toggle" -> now.status != before.status
        else -> {
            // Çoğu oynatıcı şarkının başındaysa öncekine, değilse başa döner
            val rewound = action == "previous" && now.position != null && before.position != null &&
                now.position < before.position
            now.title != before.title || rewound
        }
    }

    private fun label(packageName: String): String = try {
        val manager = context.packageManager
        manager.getApplicationLabel(manager.getApplicationInfo(packageName, 0)).toString()
    } catch (_: PackageManager.NameNotFoundException) {
        packageName
    }
}

/** Komut sonucunun gövdesi (ports/devices.py `CommandResult`), `id`'siz. */
data class Result(val status: String, val data: JSONObject, val error: String?) {
    companion object {
        fun ok(data: JSONObject) = Result("ok", data, null)
        fun error(error: String, data: JSONObject = JSONObject()) = Result("error", data, error)
    }
}

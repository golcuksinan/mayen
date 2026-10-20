package mayen.phone

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder

private const val CHANNEL = "voice"

// Bağlantının ve sesin yaşadığı ön plan hizmeti: ekran kapanınca, uygulama arkadayken de
// dinler. Bildirimi mikrofonun açık olduğunu gösterir.
class VoiceService : Service() {
    private var link: Link? = null

    override fun onCreate() {
        super.onCreate()
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL, "Listening", NotificationManager.IMPORTANCE_LOW),
        )
        val open = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = Notification.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("Mayen")
            .setContentText("Listening")
            .setContentIntent(open)
            .setOngoing(true)
            .build()
        startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        link = Link(this, BuildConfig.CORE_URL).also(Link::start)
    }

    override fun onDestroy() {
        link?.stop()
        link = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}

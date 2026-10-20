package mayen.phone

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.provider.Settings
import android.view.WindowInsets
import android.widget.FrameLayout
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.webkit.WebViewAssetLoader

private const val BACKGROUND = "#0B0D11" // arayüzün zemini (desktop/)

// Ekran: masaüstü istemcisinin arayüzü (desktop/), uygulamanın içinden açılır. Sayfa çekirdeğe
// bir şey göndermez; mesajlarını hizmetteki bağlantıdan alır (Screen).
class MainActivity : Activity() {
    private lateinit var page: WebView

    companion object {
        var current: MainActivity? = null // çıkış hizmetten de istenir (bildirim)
            private set
    }

    // Sayfadaki çıkış düğmesi (desktop/src/App.tsx); yalnızca bu nesne varken görünür
    private inner class App {
        @JavascriptInterface
        fun quit() = runOnUiThread { quit(this@MainActivity) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        current = this
        // Derlenmiş arayüz göreli yollarla açılır; file:// modül betiklerini yüklemez
        val assets = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()
        page = WebView(this).apply {
            setBackgroundColor(Color.parseColor(BACKGROUND))
            settings.javaScriptEnabled = true
            addJavascriptInterface(App(), "mayenApp")
            webViewClient = object : WebViewClient() {
                override fun shouldInterceptRequest(
                    view: WebView,
                    request: WebResourceRequest,
                ): WebResourceResponse? = assets.shouldInterceptRequest(request.url)

                override fun onPageFinished(view: WebView, url: String) = Screen.attach(view)
            }
            loadUrl("https://appassets.androidplatform.net/assets/index.html")
        }
        // Android 15'ten beri pencere ekranın kenarına uzanır; sayfa sistem çubuklarının altında
        // kalmasın. WebView kendi kenar boşluğunu yok sayar: boşluk onu taşıyan kaptadır.
        val frame = FrameLayout(this).apply {
            setBackgroundColor(Color.parseColor(BACKGROUND))
            addView(page)
            setOnApplyWindowInsetsListener { view, insets ->
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
                view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
                WindowInsets.CONSUMED
            }
        }
        setContentView(frame)
        val missing = arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.POST_NOTIFICATIONS)
            .filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isEmpty()) listen() else requestPermissions(missing.toTypedArray(), 0)
    }

    override fun onRequestPermissionsResult(code: Int, permissions: Array<out String>, results: IntArray) {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) listen()
    }

    override fun onDestroy() {
        if (current === this) current = null
        Screen.detach(page)
        page.destroy()
        super.onDestroy()
    }

    private fun listen() {
        // Medya yeteneği bildirim erişimiyle açılır; verilince bir sonraki bağlantıda bildirilir
        if (!Media(this).available()) startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        startForegroundService(Intent(this, VoiceService::class.java))
    }
}

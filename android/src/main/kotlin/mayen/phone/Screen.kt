package mayen.phone

import android.os.Handler
import android.os.Looper
import android.webkit.WebView
import org.json.JSONObject

// Bağlantıdan sayfaya giden çağrılar (desktop/src/screen.ts); bağlantı hizmette, sayfa
// etkinlikte yaşar. Etkinlik yeniden açılınca sayfa boş başlar: bağlantının son durumu ve bu
// bağlantıdaki mesajlar saklanır, her yüklenen sayfaya baştan verilir, en eskisi düşerek.
object Screen {
    private const val KEPT = 500

    private val main = Handler(Looper.getMainLooper())
    private val messages = ArrayDeque<String>()
    private var connection: String? = null
    private var page: WebView? = null

    fun message(raw: String) = main.post {
        val js = "window.mayenScreen(${JSONObject.quote(raw)})"
        if (messages.size == KEPT) messages.removeFirst()
        messages.addLast(js)
        page?.evaluateJavascript(js, null)
    }

    // Yeni bağlantının oturumu boş başlar; öncekinin mesajları yeni sayfaya verilmez
    fun connection(state: String) = main.post {
        val js = "window.mayenConnection(${JSONObject.quote(state)})"
        if (state == "connecting") messages.clear()
        connection = js
        page?.evaluateJavascript(js, null)
    }

    // Sayfa yüklenince; ana iş parçacığında
    fun attach(view: WebView) {
        page = view
        connection?.let { view.evaluateJavascript(it, null) }
        for (js in messages) view.evaluateJavascript(js, null)
    }

    fun detach(view: WebView) {
        if (page === view) page = null
    }
}

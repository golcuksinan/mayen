// Telefon istemcisi (§7, §13). Ekran `desktop/`'un derlenmiş hâlidir (önce `npm run build`);
// çekirdeğin adresi depoya girmeyen `local.properties`'ten okunur (`mayen.url`).
import java.util.Properties

plugins {
    id("com.android.application") version "9.4.1"
}

val local = Properties().apply {
    rootProject.file("local.properties").takeIf { it.exists() }?.reader()?.use(::load)
}
val coreUrl: String = local.getProperty("mayen.url")
    ?: error("local.properties: mayen.url is missing, like ws://<tailnet name>:8765/voice")

android {
    namespace = "mayen.phone"
    compileSdk {
        version = release(37) { minorApiLevel = 2 }
    }

    defaultConfig {
        applicationId = "mayen.phone"
        minSdk = 31
        targetSdk = 36
        versionCode = 1
        versionName = "0.1"
        buildConfigField("String", "CORE_URL", "\"$coreUrl\"")
    }

    buildFeatures {
        buildConfig = true
    }

    sourceSets["main"].assets.directories.add("../desktop/dist")
}

dependencies {
    implementation("com.squareup.okhttp3:okhttp:5.5.0")
    implementation("androidx.webkit:webkit:1.17.1")
}

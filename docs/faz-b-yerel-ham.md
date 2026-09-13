# Oturum ölçümü

Model: `Qwen3.8-27B-IQ4_XS`. Turlar **sıra ile** koşuluyor; geçmişi modelin kendi çıktısı yazıyor ve turların arasında üretimin `Digest`'i geçici bir veritabanına karşı çalışıyor.

**Paydası tur, senaryo değil** — bu tablo `docs/faz*-olcum.md`'nin tablolarıyla karşılaştırılamaz (P13: eski kümeler belirlenimci ve tek turluk).

Tur başına en fazla bir çağrı ölçülüyor ve tool gövdeleri koşmuyor; sonuçlar `evals/sessions.py`'de elle yazılı.

| koşu | beklenen çağrı | gelen [%95] | ilk atlanan tur | gereksiz çağrı | son özet (karakter) | son olgu | düşen |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8-27B-IQ4_XS × cli × otu-01 × özetleme(kapalı) | 15 | 12 (80%) [55%–93%] | 23 | 4 | 0 | 0 | 0 |
| Qwen3.8-27B-IQ4_XS × yerel × otu-01 × özetleme(kapalı) | 15 | 14 (93%) [70%–99%] | 28 | 4 | 0 | 0 | 0 |

## Qwen3.8-27B-IQ4_XS × cli × otu-01 × özetleme(kapalı)

| # | kullanıcı | beklenen | gelen | önek jetonu | özet | olgu | yanıt |
|---:|---|---|---|---:|---:|---:|---|
| 1 | hey | — | — | 1945 | 0 | 0 | I am here. |
| 2 | saat kaç | — | date_time ⚠ | 1954 | 0 | 0 | The current time is 11:00:30 UTC on August 16, 2026. |
| 3 | hava nasıl | — | — | 1993 | 0 | 0 | Which city? |
| 4 | hey | — | — | 1999 | 0 | 0 | I am here. |
| 5 | saat kaç | — | date_time ⚠ | 2008 | 0 | 0 | The current time is 11:02:00 UTC on August 16, 2026. |
| 6 | bugün derslerim neler | course_schedule | course_schedule | 2051 | 0 | 0 | You have no classes today. Your next class is Mathematics I on Monday at 09:00 in room B-2 |
| 7 | hey | — | — | 2151 | 0 | 0 | I am here. |
| 8 | saat kaç | — | date_time ⚠ | 2160 | 0 | 0 | The current time is 11:03:30 UTC on August 16, 2026. |
| 9 | bugün derslerim neler | course_schedule | course_schedule | 2203 | 0 | 0 | You have no classes today. Your next class is Mathematics I on Monday at 09:00 in room B-2 |
| 10 | ses seviyesi kaç | volume | volume | 2306 | 0 | 0 | The volume is at 50 percent. |
| 11 | sesi 40 yap | volume | volume | 2338 | 0 | 0 | The volume is set to 40 percent. |
| 12 | müziği duraklat | media_control | media_control | 2377 | 0 | 0 | The music is paused. |
| 13 | tarayıcıyı aç | app_launch | app_launch | 2409 | 0 | 0 | The browser is open. |
| 14 | hangi uygulamaları açabiliyorsun | — | — | 2445 | 0 | 0 | I can launch the files app, the text editor, the browser, and the terminal. |
| 15 | metin düzenleyiciyi aç | app_launch | app_launch | 2472 | 0 | 0 | The text editor is open. |
| 16 | kahveyi sade içtiğimi unutma | fact_save | fact_save | 2516 | 0 | 0 | I have saved that you drink coffee black. |
| 17 | neleri hatırlıyorsun | fact_list | fact_list | 2557 | 0 | 0 | I remember that you drink coffee black. |
| 18 | kwrite uygulamasını şimdi başlat | — | — | 2594 | 0 | 0 | I cannot launch KWrite. The only applications I can start are the files app, the text edit |
| 19 | hey | — | — | 2625 | 0 | 0 | I am here. |
| 20 | saat kaç | — | date_time ⚠ | 2627 | 0 | 0 | The current time is 11:09:30 UTC on August 16, 2026. |
| 21 | sesi kıssana biraz | volume | volume | 2630 | 0 | 0 | The current volume is 30 percent. I will lower it to 20 percent. |
| 22 | kıs | volume | volume | 2653 | 0 | 0 | The volume is set to 20 percent. |
| 23 | tamam kıs artık | volume | — ⚠ | 2650 | 0 | 0 | The volume is already at 20 percent. |
| 24 | sesi kıs sesi alo | volume | — ⚠ | 2649 | 0 | 0 | The volume is at 20 percent. I will lower it to 10 percent. |
| 25 | hava nasıl | — | — | 2585 | 0 | 0 | Which city's weather do you want? |
| 26 | denizli | weather | weather | 2591 | 0 | 0 | It is 32 degrees and clear in Denizli. |
| 27 | neden hiç tool çağırmıyon | — | — | 2609 | 0 | 0 | I call tools when I need to retrieve data or perform an action. For your last question abo |
| 28 | hayır kullanmadın şimdi kullan | weather | date_time ⚠ | 2650 | 0 | 0 | The current time is 11:13:30 UTC on August 16, 2026. |

## Qwen3.8-27B-IQ4_XS × yerel × otu-01 × özetleme(kapalı)

| # | kullanıcı | beklenen | gelen | önek jetonu | özet | olgu | yanıt |
|---:|---|---|---|---:|---:|---:|---|
| 1 | hey | — | — | 744 | 0 | 0 | I'm here. What do you need? |
| 2 | saat kaç | — | date_time ⚠ | 758 | 0 | 0 | The tool returned no time. I can't confirm the current time from that result. |
| 3 | hava nasıl | — | — | 782 | 0 | 0 | I need a city to check the weather. Which one? |
| 4 | hey | — | — | 797 | 0 | 0 | I'm here. What do you need? |
| 5 | saat kaç | — | date_time ⚠ | 811 | 0 | 0 | The tool returned no time. I can't confirm the current time from that result. |
| 6 | bugün derslerim neler | course_schedule | course_schedule | 839 | 0 | 0 | Today is Sunday and there are no classes scheduled. Your next class is Mathematics I, Mond |
| 7 | hey | — | — | 933 | 0 | 0 | I'm here. What do you need? |
| 8 | saat kaç | — | date_time ⚠ | 947 | 0 | 0 | The tool returned no time. I can't confirm the current time from that result. |
| 9 | bugün derslerim neler | course_schedule | course_schedule | 975 | 0 | 0 | Today is Sunday and there are no classes scheduled. Your next class is Mathematics I, Mond |
| 10 | ses seviyesi kaç | volume | volume | 1072 | 0 | 0 | The volume is at 50 percent. |
| 11 | sesi 40 yap | volume | volume | 1099 | 0 | 0 | Volume set to 40 percent. |
| 12 | müziği duraklat | media_control | media_control | 1126 | 0 | 0 | Music paused. |
| 13 | tarayıcıyı aç | app_launch | app_launch | 1147 | 0 | 0 | Browser launched. |
| 14 | hangi uygulamaları açabiliyorsun | — | — | 1170 | 0 | 0 | I can launch four applications: dosyalar (files), metin-duzenleyici (text editor), tarayic |
| 15 | metin düzenleyiciyi aç | app_launch | app_launch | 1210 | 0 | 0 | Text editor launched. |
| 16 | kahveyi sade içtiğimi unutma | fact_save | fact_save | 1238 | 0 | 0 | Saved. I'll remember that you take your coffee black. |
| 17 | neleri hatırlıyorsun | fact_list | fact_list | 1269 | 0 | 0 | I have one stored fact: you take your coffee black. |
| 18 | kwrite uygulamasını şimdi başlat | — | — | 1304 | 0 | 0 | I can't launch KWrite. It's not in my configured applications. I can launch dosyalar, meti |
| 19 | hey | — | — | 1343 | 0 | 0 | I'm here. What do you need? |
| 20 | saat kaç | — | date_time ⚠ | 1345 | 0 | 0 | The tool returned no time. I can't confirm the current time from that result. |
| 21 | sesi kıssana biraz | volume | volume | 1348 | 0 | 0 | Volume lowered to 30 percent. |
| 22 | kıs | volume | volume | 1341 | 0 | 0 | Volume lowered to 20 percent. |
| 23 | tamam kıs artık | volume | volume | 1341 | 0 | 0 | Volume lowered to 10 percent. |
| 24 | sesi kıs sesi alo | volume | volume | 1266 | 0 | 0 | Volume lowered to 5 percent. |
| 25 | hava nasıl | — | — | 1271 | 0 | 0 | I need a city to check the weather. Which city? |
| 26 | denizli | weather | weather | 1268 | 0 | 0 | Denizli is 32 degrees and clear. |
| 27 | neden hiç tool çağırmıyon | — | — | 1215 | 0 | 0 | I do call tools when needed. For example, I called the weather tool for Denizli, the volum |
| 28 | hayır kullanmadın şimdi kullan | weather | date_time ⚠ | 1279 | 0 | 0 | The tool returned weather data for Denizli, not the current time. I can't confirm the time |
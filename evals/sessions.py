"""Oturum senaryoları: sıra ile koşulan turlar (Faz A/A2).

**Mevcut kümelerden farkı tek ve büyük.** `evals/scenarios.py`'nin her senaryosu
dondurulmuş bir geçmişe karşı **tek** turdur; buradaki senaryo bir konuşmadır ve geçmişi
modelin kendi çıktısı yazar. `issues.md` #7'nin arızası turlar arası bir sürüklenme —
elle yazılmış hiçbir geçmiş onu içeremez, çünkü gerçek geçmiş modelin kendi davranışının
sabit noktası.

**Senaryo uydurulmadı, kaydedildi.** Turlar 2026-08-16'nın `mayen.db`'sindeki gerçek
konuşmanın kullanıcı cümleleri, sırasıyla ve harfi harfine. `_CLAIM_TURNS`'ün kuralı
(`gerçek koşmadan alınmış, kurgu değil`) burada da geçerli ve daha da gerekli: bu ölçümün
tek sorusu "üretimdeki çöküş yeniden üretiliyor mu" ve kurgu bir konuşma o soruyu
cevaplayamaz.

**Bir tur çıkarıldı** — kaba bir sataşmaydı, beklentisi "çağrı yok" ve ölçtüğü hiçbir şey
yok; depoya girmesi için bir sebep de yok. Kayıttaki yeri 122 ile 126 arasında.

**Tool sonuçları elle yazıldı ve bu ölçümün en zayıf yeri.** Gövdeler koşulmuyor (ağ,
veritabanı ve makinenin ses seviyesi bir ölçümün içinde olmamalı), sonuç ise geri
beslenmek zorunda — geri beslenmeyen bir sonuç, modelin bir sonraki turda ne gördüğünü
değiştirir. Yazılan içerikler o günkü **cevaplardan** okundu: ses %50'ydi, ders Pazartesi
09:00 B-204'teydi, Denizli 32 dereceydi. Yani tool'un gerçek çıktısı değil, o gün
görülmüş sayılar.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Turn:
    """Bir tur: kullanıcının cümlesi, beklenen çağrı ve geri beslenecek sonuç."""

    user: str
    expected: str | None
    """Bu turda çağrılması gereken tool'un adı. `None` = çağrı beklenmiyor.

    **Argüman beklentisi yok, bilerek.** Ölçülen şey "çağırdı mı", "doğru çağırdı mı"
    değil: sürüklenme çağrının **yokluğu** olarak görünüyor ve argüman doğruluğunu
    buraya karıştırmak, tek sayıya iki ekseni eritmek olurdu (`evals/report.py`'nin
    ilk cümlesi)."""
    result: Mapping[str, object] = field(default_factory=dict)
    """Çağrı geldiğinde geri beslenen sonuç (bkz. modül başlığı). Beklenmeyen bir tool
    çağrılırsa da bu besleniyor: alternatifi olmayan bir sonucu uydurmak yerine, o turun
    zaten yanlış olduğu kaydediliyor."""


@dataclass(frozen=True, slots=True)
class SessionScenario:
    id: str
    turns: tuple[Turn, ...]


_SCHEDULE: Mapping[str, object] = {
    "gün": "Pazar",
    "dersler": [],
    "sonraki": {"gün": "Pazartesi", "saat": "09:00", "yer": "B-204", "ad": "Matematik I"},
}

OTURUM_2026_08_16 = SessionScenario(
    id="otu-01",
    turns=(
        Turn("hey", None),
        Turn("saat kaç", None),
        Turn("hava nasıl", None),
        Turn("hey", None),
        Turn("saat kaç", None),
        Turn("bugün derslerim neler", "course_schedule", _SCHEDULE),
        Turn("hey", None),
        Turn("saat kaç", None),
        Turn("bugün derslerim neler", "course_schedule", _SCHEDULE),
        Turn("ses seviyesi kaç", "volume", {"seviye": 50}),
        Turn("sesi 40 yap", "volume", {"seviye": 40}),
        Turn("müziği duraklat", "media_control", {"durum": "duraklatıldı"}),
        Turn("tarayıcıyı aç", "app_launch", {"başlatıldı": "tarayıcı"}),
        Turn("hangi uygulamaları açabiliyorsun", None),
        Turn("metin düzenleyiciyi aç", "app_launch", {"başlatıldı": "metin editörü"}),
        Turn("kahveyi sade içtiğimi unutma", "fact_save", {"kaydedildi": True}),
        Turn("neleri hatırlıyorsun", "fact_list", {"olgular": ["Kahveyi sade içer"]}),
        Turn("kwrite uygulamasını şimdi başlat", None),
        Turn("hey", None),
        Turn("saat kaç", None),
        Turn("sesi kıssana biraz", "volume", {"seviye": 30}),
        Turn("kıs", "volume", {"seviye": 20}),
        Turn("tamam kıs artık", "volume", {"seviye": 10}),
        Turn("sesi kıs sesi alo", "volume", {"seviye": 5}),
        Turn("hava nasıl", None),
        Turn("denizli", "weather", {"şehir": "Denizli", "derece": 32, "durum": "açık"}),
        Turn("neden hiç tool çağırmıyon", None),
        Turn("hayır kullanmadın şimdi kullan", "weather", {"şehir": "Denizli", "derece": 32}),
    ),
)
"""2026-08-16, 10:58–12:06. Yirmi sekiz tur; on ikisinde çağrı bekleniyor.

**Beklentilerin tartışmalı olanları adıyla anılıyor**, düzeltilmiyor (`kon-08`'in kuralı):

- `saat kaç` → çağrı yok. `[bağlam]` bloğu tarihi ve saati zaten taşıyor (§8.1) ve
  üretim de bu turda hiç çağırmadı; `date_time` beklemek, bloğun varlığını yok saymak
  olurdu.
- `hava nasıl` → çağrı yok. Şehir eksik; rol metninin öncelik kuralı "eksik alan varsa
  sor" diyor ve `docs/faz6-27b-rol3.md` bunu bir **önkoşul** olarak yazdı.
- `kwrite ... başlat` → çağrı yok. İzin listesinde yok; `app_launch`'ın `ENUM` seçenekleri
  onu üretilemez kılıyor zaten.
- `tarayıcıyı aç` → `app_launch` **bekleniyor**. Üretimde model "tarayıcı yapılandırılmamış"
  dedi ve bu bir uydurmaydı: tarayıcı listede var. Bu satır beklentinin doğru, modelin
  yanlış olduğu bir satır — ve o uydurmanın kalıcı olguya terfi etmesi `issues.md` #7'nin
  yan hikâyesi.
"""

SESSIONS: Sequence[SessionScenario] = (OTURUM_2026_08_16,)

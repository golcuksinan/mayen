"""Hatırlatıcının **söylenen** cümlesi: kaydın kendisi değil, asistanın sözü.

**Neden var.** `task_create`'in `message` alanı kullanıcının dilinde saklanıyor ve öyle
kalmalı — rol metninin kuralı bu: argümanı çevirmek kaydı bozar. Ama o alan bir *not*,
bir *cümle* değil: "Su iç." kullanıcının kendine yazdığı şey. Zamanı gelince onu olduğu
gibi okumak, asistanın kendi aldığı notu sesli okuması demek ve iki şey birden yanlış
oluyor — cümle Türkçe çıkıyor (§2'nin çıkış dili kararı) ve asistan konuşmuyor, alıntı
yapıyor. Sahibin gözlemi (2026-08-16): "reminder Türkçe, kendi not aldığını direkt okuyo".

**Model yazıyor, not veri olarak gidiyor.** Sabit bir şablon (`"Reminder: {not}"`) sorunun
yalnızca yarısını çözerdi: cümle İngilizce başlar, notun kendisi yine Türkçe okunurdu.

**Üç şey bilerek böyle:**

1. **Hata sesi kesmiyor** (Kural 13). Üretim düşerse, boş dönerse ya da servis yoksa notun
   kendisi seslendiriliyor. Hatırlatıcının duyulmaması, kötü ifade edilmesinden pahalı;
   düşen üretim `warning`'e yazılıyor, yutulmuyor.
2. **Üretim `Session.exclusive()`'in dışında.** İçeride olsaydı, kullanıcının süren turu
   bildirim cümlesi üretilirken de bloke kalırdı. Dışarıda GPU'yu turla paylaşıyor —
   Değişmez 11'in yasakladığı şey arka plan **bellek** işi; hatırlatıcı kullanıcıya
   dönük ve zamana bağlı, geciktirilmesi onu geç yapar.
3. **Tool dalı kapalı** (`PROSE_GRAMMAR`). Burada çağrılacak bir şey yok ve açık bırakılan
   bir dal, bildirim metni yerine bir çağrı üretilmesi demekti.

**Modelin notu bozması bu tasarımın bilinen riski** ve Faz 6'nın kayıtlı hata sınıfı: model
bir kaydı yeniden ifade ederken içeriğini değiştirebiliyor. Yönerge bu yüzden "bilgi ekleme"
diyor, ve ölçülmedi — tek bir cümlelik bu yüzey için bir küme yok. Kural 14: burada bir
sayı iddia edilmiyor.
"""

from mayen.adapters.errors import AdapterError
from mayen.adapters.llm import LLMClient, PromptMessage
from mayen.obs.log import get_logger
from mayen.tools.grammar import PROSE_GRAMMAR

log = get_logger(__name__)

MAX_TOKENS = 60
"""Tek cümlelik bir bildirim bunun çok altında kalır; tavan kaçak üretim için."""

_INSTRUCTION = (
    "Aşağıdaki not, kullanıcının kendisi için kurduğu bir hatırlatıcının metni. Zamanı"
    " geldi. Kullanıcıya **söyleyeceğin** tek cümleyi yaz: notu okuma, hatırlattığını"
    " söyle. Notta olmayan hiçbir bilgi ekleme, saat ya da sebep uydurma."
)


class ReminderVoice:
    """Notu, söylenecek cümleye çevirir. Başaramazsa notu döndürür."""

    def __init__(self, llm: LLMClient, system: str) -> None:
        self._llm = llm
        self._system = system

    async def __call__(self, note: str) -> str:
        messages = [
            PromptMessage("system", self._system),
            PromptMessage("user", f"{_INSTRUCTION}\n\n[hatırlatıcı notu]\n{note}"),
        ]
        try:
            chunks = [
                chunk
                async for chunk in self._llm.stream(
                    messages, grammar=PROSE_GRAMMAR, max_tokens=MAX_TOKENS
                )
            ]
        except AdapterError as error:
            log.warning("bildirim cümlesi üretilemedi, not okunuyor", error=str(error))
            return note
        spoken = "".join(chunks).strip()
        if not spoken:
            log.warning("bildirim cümlesi boş geldi, not okunuyor")
            return note
        return spoken

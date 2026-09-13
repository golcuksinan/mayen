"""Onay akışı ve onay çözümleyicisi (§8.5, Kural 5).

**Anahtar kelime araması yok.** "Tamam ama önce hava durumu" cümlesini onay saymak
tasarımın kabul etmediği bir hatadır, o yüzden burada `"tamam" in text` biçiminde tek bir
satır bile yok. Segment modele **kısıtlı çıktıyla** verilir: gramer üç sözcükten başkasını
üretilemez kılar, dolayısıyla ayrıştırma diye bir aşama kalmaz.

**Zaman aşımı = red** (Kural 5). Sayacın *değeri* burada uydurulmuyor: doküman bir süre
vermiyor, bu yüzden `timeout_seconds` varsayılansız bir kurucu argümanı. Beklemeyi kim
yürütürse (P7) süreyi de dışarıdan verir; süre dolduğunda çağıracağı şey `timed_out()`.

**Bekleyen plan opak.** Tool şemaları `tools`'ta (rütbe 5) ve `policy` (6) onları import
edemez; zaten etmemeli — akış planın *içeriğine* hiç bakmıyor, yalnızca okunacak cümleyi
taşıyor. Aynı sebeple argüman doğrulaması da burada değil: §8.5'in 1. adımı, planı kuran
tarafın işi. Akış ancak doğrulanmış bir plandan başlatılabilir, çünkü `PendingPlan` zaten
okunacak cümleyi istiyor — geçersiz argümanla o cümle kurulamaz.
"""
import re

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from mayen.adapters.llm import LLMClient, PromptMessage
from mayen.policy.authority import Decision, Identity, authorize
from mayen.policy.effects import Effect


class Resolution(StrEnum):
    """§8.5 adım 4: çözümleyicinin üç sonucu."""

    ONAY = "ONAY"
    RED = "RED"
    BELIRSIZ = "BELİRSİZ"


class Outcome(StrEnum):
    """Akışın dışarıya bildirdiği sonuç. `TEKRAR_SOR` tek ara durum (§8.5 adım 5)."""

    ONAYLANDI = "ONAYLANDI"
    REDDEDILDI = "REDDEDİLDİ"
    TEKRAR_SOR = "TEKRAR_SOR"


class ResolverError(Exception):
    """Model gramerin dışına çıktı. Yutulmaz (Kural 13) — belirsiz sayılmaz da.

    Belirsiz saymak, bozuk bir servisi kullanıcının kararsızlığı gibi göstermek olurdu;
    ikinci soru da aynı bozuk servise gider ve akış sessizce iptalle biter.
    """


@dataclass(frozen=True, slots=True)
class PendingPlan:
    """Onay bekleyen işlem.

    `spoken` kullanıcıya okunan cümledir (§8.5 adım 3) ve akışa girmeden önce kurulur;
    kurulabilmesi argümanların doğrulanmış olması demektir.
    """

    tool: str
    spoken: str


# Üç sözcükten başkası üretilemez. Dallanma ilk token'da belli (§6) — üç seçenek de farklı
# harfle başlıyor, model ilk token'ı verdiğinde sonuç zaten bellidir.
#GRAMMAR = 'root ::= "ONAY" | "RED" | "BELİRSİZ"'
GRAMMAR = r'''root ::= think? [ \t\n]* ("ONAY" | "RED" | "BELİRSİZ")
think ::= "<think>" [^<]* "</think>"'''

#: **Sorulan şey de veriliyor** ve bu ölçülmüş bir hatanın karşılığı (2026-08-16): soru
#: verilmezken "Close the active window?" sorusuna sahibin verdiği `kapat` cevabı üç
#: koşuda üçünde **RED** okundu. Bağlamsız bir emir kipi evet/hayır ekseninde durmuyor;
#: oysa isteği tekrarlamak insanın onaylamasının en doğal yolu. `evet`, `tamam`, `olur`,
#: `kapatabilirsin` aynı koşuda doğru okunuyordu — yani eksik olan model değil, soruydu.
#: Kural 5 bozulmuyor: hâlâ anahtar kelime araması yok, karar hâlâ üç sözcüklük gramerin
#: içinde. Planın *içeriği* değil, sahibe okunan cümle gidiyor (bkz. `PendingPlan.spoken`).
_SYSTEM = (
    "You are an intent classifier for user confirmation in an asymmetric voice assistant.\n"
    "The system asks confirmation in English, but the Administrator usually replies in Turkish (or English).\n\n"
    "Classify the user's response into exactly one token:\n"
    "- ONAY: The user agrees, approves, or repeats the action to be done.\n"
    "  Examples in Turkish: 'evet', 'sil', 'evet sil', 'tamam', 'onaylıyorum', 'yap', 'olur', 'kapat'.\n"
    "  Examples in English: 'yes', 'confirm', 'confirmed', 'delete', 'please delete', 'do it', 'sure'.\n"
    "- RED: The user explicitly refuses or cancels.\n"
    "  Examples in Turkish: 'hayır', 'iptal', 'vazgeç', 'silme', 'dur'.\n"
    "  Examples in English: 'no', 'cancel', 'don't', 'stop'.\n"
    "- BELİRSİZ: The user asks an unrelated question or the intent is ambiguous."
)


def needs_approval(identity: Identity, effect: Effect) -> bool:
    """Onay gerekiyor mu — kararı yine tek kapı veriyor (Kural 4)."""
    return authorize(identity, effect) is Decision.ONAY_GEREKLI


class ApprovalResolver:
    """Segmenti üç sonuçtan birine çevirir. Başka hiçbir şey yapmaz."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def resolve(self, text: str, *, question: str) -> Resolution:
        messages: Sequence[PromptMessage] = (
            PromptMessage(role="system", content=_SYSTEM),
            PromptMessage(role="user", content=f"Sorulan: {question}\nYanıt: {text}"),
        )
        for m in messages:
            print(f"DEBUG PROMPT [{m.role}]: {m.content}")
        chunks: list[str] = []
        async for chunk in self._llm.stream(messages, grammar=GRAMMAR):
            chunks.append(chunk)
        #answer = "".join(chunks).strip()
        raw_answer = "".join(chunks).strip()

# Eğer </think> varsa, öncesindeki tüm düşünme sürecini (açılış etiketi olsa da olmasa da) at
        if "</think>" in raw_answer:
            answer = raw_answer.split("</think>")[-1].strip()
        else:
            # Açılmamış/kapanmamış <think> varsa temizle
            answer = re.sub(r"<think>.*", "", raw_answer, flags=re.DOTALL).strip()
        print(f"DEBUG RESOLVER: Girdi: {text!r} -> Çıkan Karar: {answer!r}")
        try:
            return Resolution(answer)
        except ValueError as exc:
            raise ResolverError(f"gramer dışı yanıt: {answer!r}") from exc


class ApprovalFlow:
    """Tek bir planın onay akışı: en fazla iki soru, sonra red (§8.5 adım 5-6).

    Sayaç burada çünkü §10 onayın sahibi; oturum aktörü yalnızca sonucu olaya çevirir.
    """

    def __init__(
        self, plan: PendingPlan, resolver: ApprovalResolver, *, timeout_seconds: float
    ) -> None:
        self.plan = plan
        self.timeout_seconds = timeout_seconds
        self._resolver = resolver
        self._asked_again = False

    async def resolve_segment(self, text: str) -> Outcome:
        resolution = await self._resolver.resolve(text, question=self.plan.spoken)
        if resolution is Resolution.ONAY:
            return Outcome.ONAYLANDI
        if resolution is Resolution.RED:
            return Outcome.REDDEDILDI
        if self._asked_again:
            # İkinci belirsiz yanıt: işlem iptal edilir. Israr etmek, kullanıcının
            # anlamadığı bir soruyu üçüncü kez sormak demek.
            return Outcome.REDDEDILDI
        self._asked_again = True
        return Outcome.TEKRAR_SOR

    def timed_out(self) -> Outcome:
        """Kural 5: zaman aşımı reddir. Tekrar sorma hakkı varken bile."""
        return Outcome.REDDEDILDI

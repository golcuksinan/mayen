"""Boştaki bellek işi: olgu çıkarımı ve özetleme (§11.2, §11.3).

**Tek iş, iki çıktı — ve bunun sebebi filigran.** İkisini ayrı işler yapmak, "hangi
mesajlar işlendi" sorusunu iki kez cevaplamak demekti: özetlemenin cevabı zaten şemada
(`messages.summary_id`), çıkarımınki ise ikinci bir sütun ya da ikinci bir tablo isterdi.
Aynı yığın üzerinde önce olgular çıkarılıp sonra özet yazıldığında, `summary_id`'nin
yazılması ikisinin birden filigranı oluyor.

**En yeni mesajlar yığına girmiyor.** Pencerede hâlâ kelimesi kelimesine duran bir mesajı
özetlemek, modele aynı konuşmayı iki kez —biri özet, biri ham— vermek olurdu. Sınır
`keep_recent`: pencerenin kuyruğu kadar mesaj her zaman özetin dışında kalır. Canlı
pencerenin o anki sınırına bakmak daha dar olurdu ama yeniden başlatma o sınırı siler;
sayının işletim değeri olması bu yüzden.

**Özet birikimli.** `latest()` tek bir özet döndürüyor (§11.1'in dizilimi de tek bir özet
bloğu koyuyor), yani yeni özet eskisinin yerine geçiyor. Eski özet prompt'a konmasaydı
kapsadığı konuşma sessizce buharlaşırdı.

**Yarım kalan yazılmaz** (§11.3). İş iptal edildiğinde `CancelledError` üretimin ortasında
yükseliyor ve buradaki hiçbir yazma çalışmıyor; bir sonraki boşlukta aynı yığın baştan
işleniyor.

**Aynı olgu iki kez yazılmıyor.** Çıkarım ile özet arasında iş iptal edilirse yığın bir
daha işlenir; birebir aynı metin zaten varsa atlanıyor. Kişi hakkında ikinci kez "adı Ali"
diyen bir depo, kullanıcının silmek zorunda kalacağı bir depodur (§11.3).
"""

import re
from dataclasses import dataclass

from mayen.adapters.llm import LLMClient, PromptMessage
from mayen.data.repositories.conversation import Message, MessageRepository, SummaryRepository
from mayen.data.repositories.facts import FactRepository
from mayen.obs.log import get_logger

log = get_logger(__name__)

_FACT_PROMPT = (
    "Aşağıdaki konuşmadan kalıcı olarak hatırlanmaya değer olguları çıkar. Her olguyu tek"
    " satırda, tire ile başlayarak yaz. Yalnızca kişilerin kalıcı bilgilerini yaz:"
    " tercihleri, ilişkileri, sürekli durumları. Geçici şeyleri (hava durumu, saat, tek"
    " seferlik istekler) yazma. Hatırlanacak bir şey yoksa yalnızca YOK yaz."
)

_SUMMARY_PROMPT = (
    "Aşağıdaki konuşmayı Türkçe, kısa ve bilgi kaybetmeden özetle. Önceki özet varsa onu"
    " da içine al; yeni özet eskisinin yerine geçecek. Yorum ekleme, yalnızca konuşulanı"
    " aktar."
)

_NONE = "YOK"

_FACT_LINE = re.compile(r"^\s*[-*]\s*(.+?)\s*$")


@dataclass(frozen=True, slots=True)
class DigestResult:
    """Bir koşunun sonucu. Ölçüm için: hiç iş çıkmadıysa üçü de sıfır."""

    messages: int
    facts: int
    summarized: bool


class Digest:
    def __init__(
        self,
        *,
        llm: LLMClient,
        messages: MessageRepository,
        summaries: SummaryRepository,
        facts: FactRepository,
        keep_recent: int,
        batch_size: int,
        max_tokens: int,
    ) -> None:
        if keep_recent < 1:
            raise ValueError("keep_recent en az 1 olmalı")
        if batch_size < 1:
            raise ValueError("batch_size en az 1 olmalı")
        self._llm = llm
        self._messages = messages
        self._summaries = summaries
        self._facts = facts
        self._keep_recent = keep_recent
        self._batch_size = batch_size
        self._max_tokens = max_tokens

    async def run(self) -> DigestResult:
        """Bekleyen yığını işler. Kural 11: bu yalnızca boştayken çağrılır ve tur
        kuyruğa girdiği anda iptal edilir — çağıran taraf `BackgroundWork`."""
        batch = self._batch()
        if not batch:
            return DigestResult(messages=0, facts=0, summarized=False)

        conversation = _render(batch)
        previous = self._summaries.latest()

        extracted = await self._extract(conversation)
        written = self._write_facts(extracted, batch)

        summary = await self._summarize(
            conversation, None if previous is None else previous.content
        )
        self._summaries.create([m.id for m in batch], summary)
        log.info("bellek işlendi", messages=len(batch), facts=written)
        return DigestResult(messages=len(batch), facts=written, summarized=True)

    def _batch(self) -> list[Message]:
        pending = self._messages.unsummarized()
        older = pending[: max(0, len(pending) - self._keep_recent)]
        return older[: self._batch_size]

    async def _extract(self, conversation: str) -> list[str]:
        answer = await self._generate(f"{_FACT_PROMPT}\n\n{conversation}")
        if answer.strip().upper().startswith(_NONE):
            return []
        facts = []
        for line in answer.splitlines():
            match = _FACT_LINE.match(line)
            if match and match.group(1).upper() != _NONE:
                facts.append(match.group(1))
        return facts

    async def _summarize(self, conversation: str, previous: str | None) -> str:
        head = (
            _SUMMARY_PROMPT
            if previous is None
            else f"{_SUMMARY_PROMPT}\n\n[önceki özet]\n{previous}"
        )
        answer = (await self._generate(f"{head}\n\n{conversation}")).strip()
        if not answer:
            # Boş özet, kapsadığı konuşmayı hiçbir şeye çevirmek olurdu (Kural 13).
            raise ValueError("özetleyici boş yanıt verdi") #Log gürültüsünden dolayı commented out.
            #print("özetleyici boş yanıt verdi")
        return answer

    async def _generate(self, prompt: str) -> str:
        chunks = []
        async for chunk in self._llm.stream(
            (PromptMessage(role="user", content=prompt),), max_tokens=self._max_tokens
        ):
            chunks.append(chunk)
        return "".join(chunks)

    def _write_facts(self, contents: list[str], batch: list[Message]) -> int:
        """Olgular yığının **son** mesajına bağlanıyor: hangi cümleden çıktıkları
        üretimden geri okunamaz ve bir kaynak uydurmak, yanlış bir kaynak göstermek olurdu.
        Kişi de aynı sebeple yığındaki son konuşandan alınıyor."""
        source = batch[-1]
        person_id = next(
            (
                m.person_id
                for m in reversed(batch)
                if m.role == "user" and m.person_id is not None
            ),
            None,
        )
        existing = {fact.content for fact in self._facts.list_all()}
        written = 0
        for content in contents:
            if content in existing:
                continue
            self._facts.create(content, person_id=person_id, source_message_id=source.id)
            existing.add(content)
            written += 1
        return written


def _render(batch: list[Message]) -> str:
    return "\n".join(f"{message.role}: {message.content}" for message in batch)

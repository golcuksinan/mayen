"""Bağlam penceresi: bütçeye sığan konuşma (§11.1).

Oturum sınırı yok, konuşma tek sürekli akış — yani "geçmişin tamamı" diye gönderilebilecek
bir şey de yok. Bütçeye sığanı seçen yer burası.

**Sayılar sunucunun sayacından, satır satır önbelleklenerek** (Kural 10, §11.1). Bir
mesajın token sayısı bir kez sorulur ve `messages.token_count` sütununa yazılır; ikinci
turda aynı mesaj için tekrar sorulmaz. Tahmin eden bir yol bilinçli olarak yok: sayının
kaynağı tek.

**Bütçe aşılırsa sert kırpma** (§11.1): en eski mesajlar pencerenin dışında kalır.
**Silinmezler** — satır yerinde durur ve `summary_id IS NULL` olduğu için özetleme işinin
iş listesine girer. Kırpmanın kendisi bir olay: her seferinde `warning`'e yazılıyor ve
sayacı (`trims`) dışarıdan okunabiliyor, çünkü §11.1'in asıl kuralı **kırpmanın istisnai
olması**; sık kırpılıyorsa çözüm daha akıllı bir kırpma değil, bütçenin yanlış olduğunu
kabul etmek.

**Özet ve olgular pencerenin parçası ama geçmişin değil.** Özet §8.1'in sırasında geçmişin
önünde durur, olgular ise bağlam bloğunun içinde en sonda (§11.3) — ikisinin de token'ı
sabit kısımdan sayılıyor, yoksa geçmişe ayrılan yer kadar büyüyüp bütçeyi aşabilirlerdi.
"""

import json
from dataclasses import dataclass

from mayen.adapters.llm import LLMClient, NativeCall, PromptMessage
from mayen.data.repositories.conversation import (
    Message,
    MessageRepository,
    Role,
    SummaryRepository,
)
from mayen.memory.budget import Budget
from mayen.memory.recall import Recall
from mayen.obs.log import get_logger

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Window:
    """Bir turun modele gidecek geçmişi."""

    summary: str | None
    history: tuple[PromptMessage, ...]
    facts: str | None
    trimmed: int


class ContextWindow:
    def __init__(
        self,
        *,
        llm: LLMClient,
        messages: MessageRepository,
        summaries: SummaryRepository,
        recall: Recall,
        reserved_output: int,
        max_messages: int,
        digest_on: bool = True,
    ) -> None:
        if max_messages < 1:
            raise ValueError("max_messages en az 1 olmalı")
        self._llm = llm
        self._messages = messages
        self._summaries = summaries
        self._recall = recall
        self._reserved_output = reserved_output
        self._max_messages = max_messages
        #: `False` ise özet ve olgular öneğe **hiç girmez** (2026-08-16). Depolar bağlı
        #: kalıyor ve `Digest` yazmaya devam edebilir; kapanan tek şey okuma yolu. Silmek
        #: yerine kapatılmasının sebebi ölçüm: katmanın bugün faydası ölçülmedi ama
        #: zararı da ölçülmedi, ve bağlam bütçesi baskı yapmaya başladığında geri
        #: gerekecek — bugün 16384'lük pencerenin ~%19'undayız ve kırpıcı hiç çalışmadı.
        self._digest_on = digest_on
        self._budget: Budget | None = None
        #: Kaç kez kırpıldı. §11.1 sıklığın ölçülmesini istiyor; sayaç süreç ömrü boyunca.
        self.trims = 0

    def record(
        self,
        turn_id: str,
        role: Role,
        content: str,
        *,
        person_id: int | None = None,
        tool_calls: tuple[NativeCall, ...] = (),
    ) -> Message:
        """Konuşmaya bir satır ekler. Token sayısı burada **sorulmuyor**: tur sürerken
        sayaç ucuna gitmek, ilk sesin gecikmesine ölçülmemiş bir vergi eklemek olurdu
        (§6). Sayı bir sonraki pencere kurulurken bir kez sorulup satıra yazılıyor.

        `tool_calls` yalnızca yerel çağrı biçiminde dolu (`CallFormat.YEREL`): çağrı
        orada metnin **içinde** değil, mesajın yanında duruyor ve öyle saklanmalı —
        metne çevrilirse model onu bir sonraki turda kopyalıyor (`docs/faz-b-yerel.md`).
        """
        return self._messages.append(
            turn_id,
            role,
            content,
            person_id=person_id,
            tool_calls=_dump_calls(tool_calls),
        )

    async def build(self, *, fixed_text: str, person_id: int | None = None) -> Window:
        """`fixed_text`: sistem promptu, bağlam bloğu ve kullanıcının cümlesi — yani öneğin
        geçmiş dışında kalan her şeyi. Sabit kısmı çağıran biliyor, bölmeyi bütçe yapıyor.
        """
        budget = await self._ensure_budget()
        summary = self._summaries.latest() if self._digest_on else None
        facts = self._recall.block(person_id=person_id) if self._digest_on else None

        fixed = await self._llm.count_tokens(fixed_text)
        if summary is not None:
            fixed += await self._summary_tokens(
                summary.id, summary.content, summary.token_count
            )
        if facts is not None:
            fixed += await self._llm.count_tokens(facts)

        limit = budget.history_limit(fixed)
        history, trimmed = await self._fit(limit)
        return Window(
            summary=None if summary is None else summary.content,
            history=history,
            facts=facts,
            trimmed=trimmed,
        )

    async def _fit(self, limit: int) -> tuple[tuple[PromptMessage, ...], int]:
        """En yeniden geriye doğru doldurur; sığmayanlar kırpılır (§11.1).

        Sığmayan **tek bir** mesaj bulunduğunda durulmuyor, döngü de sürdürülmüyor: daha
        eski bir mesajın araya girmesi konuşmayı deliklerle dolu bir metne çevirirdi —
        modelin gördüğü şey artık olan bir konuşma olmazdı.
        """
        rows = self._messages.recent(self._max_messages)
        kept: list[Message] = []
        used = 0
        for message in reversed(rows):
            tokens = await self._tokens(message)
            if used + tokens > limit:
                break
            used += tokens
            kept.append(message)
        kept.reverse()

        trimmed = len(rows) - len(kept)
        if trimmed:
            self.trims += 1
            # §11.1: kırpma istisnai bir olay. Sessiz kalırsa bütçenin yanlış olduğu hiç
            # öğrenilmez; `warning` bu yüzden `info` değil (Kural 13).
            log.warning(
                "bağlam kırpıldı",
                trimmed=trimmed,
                kept=len(kept),
                limit=limit,
                trims=self.trims,
            )
        return tuple(
            PromptMessage(role=m.role, content=m.content, tool_calls=_load_calls(m.tool_calls))
            for m in kept
        ), trimmed

    async def _tokens(self, message: Message) -> int:
        """Satırın token sayısı; yoksa bir kez sorulup satıra yazılır (§11.1)."""
        if message.token_count is not None:
            return message.token_count
        count = await self._llm.count_tokens(message.content)
        self._messages.set_token_count(message.id, count)
        return count

    async def _summary_tokens(self, summary_id: int, content: str, cached: int | None) -> int:
        if cached is not None:
            return cached
        count = await self._llm.count_tokens(content)
        self._summaries.set_token_count(summary_id, count)
        return count

    async def _ensure_budget(self) -> Budget:
        """Bağlam boyutu servise bir kez sorulur: süreç boyunca aynı sunucu, aynı `-c`."""
        if self._budget is None:
            self._budget = Budget(
                context_size=await self._llm.context_size(),
                reserved_output=self._reserved_output,
            )
        return self._budget


def _dump_calls(calls: tuple[NativeCall, ...]) -> str | None:
    """Çağrıları saklanacak JSON metne çevirir; çağrı yoksa NULL.

    Boş listeyi `"[]"` diye yazmak, çağrı taşımayan on binlerce satıra anlamsız bir gövde
    eklemek olurdu — ve "çağrısı yok" ile "çağrı listesi boş" ayrımı hiçbir yerde
    kullanılmıyor.
    """
    if not calls:
        return None
    return json.dumps(
        [{"name": c.name, "arguments": dict(c.arguments)} for c in calls], ensure_ascii=False
    )


def _load_calls(raw: str | None) -> tuple[NativeCall, ...]:
    if raw is None:
        return ()
    return tuple(
        NativeCall(name=item["name"], arguments=item["arguments"]) for item in json.loads(raw)
    )

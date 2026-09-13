"""Ajan döngüsü (§8.2).

```
adım = 0
döngü (adım < MAX_ADIM):
    LLM'i akış modunda çağır
    tool çağrısı yoksa → metni cümle bölücüye akıt, bitir
    politika kontrolü → izin | red | onay gerekli
    izin ise → çalıştır (zaman aşımıyla); sonucu bağlama ekle, adım += 1
```

**Döngü bir üreteç.** İlk sesin gecikmesi §6'nın birinci sınıf hedefi; düz metin dalında
token'lar toplanıp sonunda dönmez, geldikleri gibi dışarı akar. Dal ilk token'da bellidir
(§6, C3): gramer tool dalını sabit bir önekle başlatıyor, düz metin o karakterle
başlayamıyor — bu yüzden buradaki tampon en fazla önek kadar, bir cümle kadar değil.

**Adım başına tek çağrı.** §8.2 çoğul yazıyor ama gramerin kökü tek üretimde tek çağrı
veriyor (`tools/grammar.py`); "her çağrı için" döngüsünü yazmak, gramerin üretemediği bir
girdiye karşı kod yazmak olurdu. Biçim değişirse değişecek yer burası, tek satır.

**Bozuk çağrı modele geri besleniyor** (§8.3). Ayrıştırma ya da doğrulama hatasında hata
metni — `ToolArgumentError` ise `usage()`'ıyla birlikte — tur bağlamına yazılıyor ve aynı
adım yeniden üretiliyor. Düzeltme turu **adım harcamıyor**: `MAX_ADIM` §8.2'nin *tool*
sayısı, modelin kendi hatasını düzeltme sayısı değil.

**Tavana ulaşınca tur ölmüyor, düz metinle kapanıyor.** Yükseltmek gerçek bir turu
öldürürdü; sessizce devam etmek Kural 13'e aykırı olurdu. İkisi de değil: olay
`log.warning`'e yazılıyor, modele ne olduğu söyleniyor ve `MAX_ADIM` dalındaki kapanışın
aynısı koşuyor — kullanıcı bir yanıt duyuyor.

**`max_corrections` varsayılansız.** Tavan bir ölçüm parametresi (`evals/runner.py` aynı
sayıyı rapora yazıyor); §19'da sayı yok, `max_steps` gibi çağıran veriyor.

**Onay bu katmanda yürümüyor.** §8.5'in `ONAY_BEKLİYOR`'u bir oturum durumu ve `session`
`agent`'in *üstünde* (§4) — döngü kararı bir `approve` geri çağrımına soruyor, o çağrımı
turu koşan taraf uyguluyor. `TurnRunner`/`SessionSink` kalıbının aynısı.

**`max_steps` varsayılansız.** §8.2 "sonlu ve küçük" diyor, sayı vermiyor; `ApprovalFlow`
zaman aşımında olduğu gibi sayıyı burada uydurmak, ölçülmemiş bir değeri koda gömmek olurdu.

**Zorunlu tool modu ölçüldü ve silindi** (P25.3, 2026-08-13). Döngünün bir de "her adımda
çağrı zorunlu" hâli vardı; `no_tool` işaretini gören dal buradan kalktı. Gerekçe
`tools/grammar.py`'nin başlığında, geri alma yaması
`docs/faz4/zorunlu-mod-geri-alma.patch`.
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping, Sequence
from contextlib import aclosing
from dataclasses import dataclass

from mayen.adapters.llm import LLMClient, NativeCall, PromptMessage
from mayen.agent.calls import (
    CallFormat,
    CallParseError,
    ToolCall,
    from_native,
    is_call,
    parse,
)
from mayen.agent.prompt import ContextBlock, build_messages
from mayen.obs.log import get_logger
from mayen.policy.approval import PendingPlan
from mayen.policy.authority import Decision, Identity, authorize
from mayen.tools.grammar import CALL_PREFIX, PROSE_GRAMMAR, cli_grammar, json_grammar
from mayen.tools.registry import Registry
from mayen.tools.schema import schemas
from mayen.tools.spec import Tool, ToolArgumentError, ToolContext, ToolResult

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TextChunk:
    """Düz metin dalından çıkan parça. Cümle bölücünün girdisi (§6)."""

    text: str


@dataclass(frozen=True, slots=True)
class ToolStarted:
    """§6: tool sonucu dönene kadar ses üretilmez; bu sırada istemciye hangi tool'un
    çalıştığı bildirilir."""

    name: str


@dataclass(frozen=True, slots=True)
class ToolDone:
    """Biten bir tool adımının **geçmişe yazılacak** hâli (2026-08-16, Faz B).

    Ajan döngüsü bu iki mesajı zaten tur içinde kuruyordu; olay onları turun dışına
    taşıyor, çünkü konuşma geçmişini yazan taraf `turn/runner.py` (§11.1) ve olay akışı
    ikisinin arasındaki tek yol.

    **Neden sonuç artık saklanıyor.** Eski kural "sonuç ertesi tur bayat, yalnızca adı
    yaz"dı (`turn/runner.py:called_line`). Ölçüm o kuralın bedelini gösterdi: sonuç
    atılınca veri geçmişte **yalnızca asistanın cevabında** kalıyor, yani modelin kendi
    bilgisi gibi duruyor ve model bir daha çağırmıyor (`docs/faz-a-bulgular.md`,
    `docs/faz-b-bicim.md`). Bayatlık ortadan kalkmıyordu, sadece kaynağı gizleniyordu.
    Sonuç `tool` rolünde durduğunda bayatlık **işaretli** oluyor: bir tool'dan geldiği ve
    ne zaman geldiği rollerden okunuyor.
    """

    name: str
    call_text: str
    """Geçmişteki `assistant` satırının **metni**.

    Metin biçimlerinde modelin ürettiği çağrının kendisi, harfi harfine. Yerel biçimde
    çağrı metin değil — orada bu alan modelin çağrıdan önce **söylediği** cümledir ve
    çoğu turda boştur."""
    feedback: str
    """`_feedback()`'in verdiği sonuç — geçmişte `tool` satırı olur."""
    tool_calls: tuple[NativeCall, ...] = ()
    """Yerel biçimde çağrının kendisi; metin biçimlerinde boş (o zaman `call_text`'in
    içinde). Geçmişe **bu biçimde** yazılmalı: model kendi ürettiği biçimi görmezse onu
    düz metin olarak kopyalıyor (ölçüldü, `docs/faz-b-yerel.md`)."""


type AgentEvent = TextChunk | ToolStarted | ToolDone

type Approver = Callable[[PendingPlan], Awaitable[bool]]
"""Onay kapısı (§8.5). `True` onay, `False` red — zaman aşımı da reddir (Kural 5) ve
sayacın sahibi `ApprovalFlow`, bu döngü değil."""

_LIMIT_NOTE = (
    "Tool çağırma hakkın bitti. Şu ana kadar aldığın sonuçlarla kullanıcıya yanıt ver;"
    " eksik kalan bir şey varsa bunu açıkça söyle."
)

_CORRECTION_NOTE = (
    "Çağrıyı düzeltme hakkın bitti. Tool çağırmadan kullanıcıya yanıt ver ve istediği şeyi"
    " yapamadığını açıkça söyle."
)


class AgentLoop:
    def __init__(
        self,
        *,
        llm: LLMClient,
        registry: Registry,
        tools: ToolContext,
        call_format: CallFormat,
        max_steps: int,
        max_corrections: int,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps en az 1 olmalı")
        if max_corrections < 0:
            raise ValueError("max_corrections negatif olamaz")
        self._llm = llm
        self._registry = registry
        self._tools = tools
        self._format = call_format
        self._max_steps = max_steps
        self._max_corrections = max_corrections
        self._native = call_format is CallFormat.YEREL
        # Yerel biçimde gramer yok: kısıt şablonun kendisinde ve `tools` şemasında.
        self._schemas = schemas(registry) if self._native else []
        if self._native:
            self._grammar = ""
        else:
            generate = cli_grammar if call_format is CallFormat.CLI else json_grammar
            self._grammar = generate(registry)

    async def run(
        self,
        system: str,
        *,
        identity: Identity,
        context: ContextBlock,
        user: str,
        approve: Approver,
        summary: str | None = None,
        history: Sequence[PromptMessage] = (),
    ) -> AsyncGenerator[AgentEvent]:
        """Bir turun ajan döngüsü. Ürettiği olaylar geldikleri anda dışarı akar."""
        turn: list[PromptMessage] = []
        note: str | None = _LIMIT_NOTE
        for step in range(self._max_steps):
            corrections = 0
            resolved: tuple[Tool, ToolCall, Mapping[str, object]] | None = None
            while True:
                messages = build_messages(
                    system,
                    context=context,
                    user=user,
                    summary=summary,
                    history=history,
                    turn=turn,
                )
                produced: str | NativeCall | None = None
                spoken: list[str] = []
                async with aclosing(self._produce(messages)) as stream:
                    async for event in stream:
                        if isinstance(event, TextChunk):
                            # Yerel biçimde model konuşup **sonra** çağırabilir; söylediği
                            # şey akmaya devam ediyor, metin biçimlerinde bu dal zaten
                            # çağrısız (§6/C3) ve döngü aşağıda bitiyor.
                            spoken.append(event.text)
                            yield event
                        else:
                            produced = event
                            if not self._native:
                                break
                if produced is None:
                    return  # düz metin dalı: tur bitti (§8.2)
                call_text = produced if isinstance(produced, str) else "".join(spoken)

                try:
                    resolved = self._resolve(produced)
                    break
                except (CallParseError, ToolArgumentError) as exc:
                    # §8.3: hata modele geri beslenir, kullanıcıya hiç sorulmaz.
                    feedback = _correction(exc)
                    log.warning(
                        "bozuk çağrı", step=step, correction=corrections, error=str(exc)
                    )
                    turn.append(_assistant(call_text, produced))
                    turn.append(PromptMessage(role="tool", content=feedback))
                    if corrections >= self._max_corrections:
                        resolved = None
                        break
                    corrections += 1

            if resolved is None:
                log.warning("düzeltme tavanına ulaşıldı", max_corrections=self._max_corrections)
                note = _CORRECTION_NOTE
                break

            tool, call, values = resolved
            yield ToolStarted(call.name)
            result = await self._invoke(tool, values, identity, approve)
            feedback = _feedback(result)
            said = _assistant(call_text, produced)
            turn.append(said)
            turn.append(PromptMessage(role="tool", content=feedback))
            yield ToolDone(call.name, call_text, feedback, said.tool_calls)
            log.info("tool adımı", tool=call.name, step=step, ok=result.ok)
        else:
            # Sınıra ulaşıldı: eldeki sonuçlarla yanıt üretilir, sessizce devam edilmez (§8.2).
            log.warning("MAX_ADIM sınırına ulaşıldı", max_steps=self._max_steps)

        # Rol `user`, `system` değil: baştan sonra gelen bir `system` mesajı Qwen3.6'nın
        # şablonunda istisna atıyor (gerekçe `agent/prompt.py`'nin başlığında).
        if note is not None:
            turn.append(PromptMessage(role="user", content=f"[not]\n{note}"))
        messages = build_messages(
            system, context=context, user=user, summary=summary, history=history, turn=turn
        )
        async with aclosing(self._generate(messages, PROSE_GRAMMAR)) as stream:
            async for event in stream:
                if isinstance(event, str):
                    raise AssertionError("düz metin grameri tool çağrısı üretti")
                yield event

    def _produce(
        self, messages: Sequence[PromptMessage]
    ) -> AsyncGenerator[TextChunk | str | NativeCall]:
        """Seçilen biçimde tek üretim. Biçime bakan **tek** yer burası ve `__init__`.

        Metin biçimlerinde çıktı ya düz metin ya çağrı (§6/C3); yerel biçimde ikisi
        birden gelebilir ve `run()` bunu bekliyor.
        """
        if self._native:
            return self._generate_native(messages)
        return self._generate(messages, self._grammar)

    async def _generate_native(
        self, messages: Sequence[PromptMessage]
    ) -> AsyncGenerator[TextChunk | NativeCall]:
        """Modelin kendi şablonuyla üretim. Tampon yok: metin metin, çağrı çağrı geliyor.

        **Adım başına tek çağrı** (§8.2, `run`'ın kuralı): sunucu birden çok döndürürse
        fazlası uyarıyla düşüyor, sessizce değil (Kural 13). Gramerle engellenemiyor —
        metin biçimlerinde bu kısıtı kökün tekliği koyuyordu.
        """
        seen = False
        stream = self._llm.stream_native(messages, tools=self._schemas)
        async with aclosing(stream) as events:
            async for event in events:
                if isinstance(event, str):
                    yield TextChunk(event)
                elif seen:
                    log.warning("adım başına tek çağrı: fazlası düştü", tool=event.name)
                else:
                    seen = True
                    yield event

    async def _generate(
        self, messages: Sequence[PromptMessage], grammar: str
    ) -> AsyncGenerator[TextChunk | str]:
        """Tek üretim. Düz metinse parçaları akıtır; tool dalıysa tek `str` olarak verir.

        Tampon yalnızca dal belli olana kadar tutulur — en fazla önek uzunluğu kadar. Tool
        dalında metnin tamamı beklenir; çağrı yarım ayrıştırılamaz.
        """
        buffer = ""
        prose = False
        call = False
        async with aclosing(self._llm.stream(messages, grammar=grammar)) as stream:
            async for chunk in stream:
                if prose:
                    yield TextChunk(chunk)
                    continue
                buffer += chunk
                if call:
                    continue
                if is_call(buffer):
                    call = True
                elif not CALL_PREFIX.startswith(buffer):
                    # Önekin başlangıcı bile olamaz: dal düz metin, tampon tek seferde boşalır.
                    prose = True
                    yield TextChunk(buffer)
        if call:
            yield buffer
        elif not prose and buffer:
            # Üretim önekin yarısında bitti; kısa ama tam bir düz metin yanıtı.
            yield TextChunk(buffer)

    def _resolve(
        self, produced: str | NativeCall
    ) -> tuple[Tool, ToolCall, Mapping[str, object]]:
        """Ham çıktı → tool + doğrulanmış argümanlar. §8.5 adım 1 burada koşuyor: hem
        ayrıştırma hem doğrulama düzeltme döngüsünün içinde kalsın diye tek yerde."""
        if isinstance(produced, NativeCall):
            call = from_native(self._registry, produced)
            tool = self._registry.get(call.name)
            return tool, call, tool.validate(call.arguments)
        call = parse(self._registry, self._format, produced)
        tool = self._registry.get(call.name)
        return tool, call, tool.validate(call.arguments)

    async def _invoke(
        self,
        tool: Tool,
        values: Mapping[str, object],
        identity: Identity,
        approve: Approver,
    ) -> ToolResult:
        """Politika → çalıştırma. Sıra pazarlığa kapalı."""
        decision = authorize(identity, tool.effect)
        if decision is Decision.RED:
            # §8.2: red bir istisna değil, modele geri beslenen sonuç — model kullanıcıya
            # neden yapamadığını anlatabilsin diye.
            return ToolResult(ok=False, error=f"yetki yok: {tool.effect.value}")
        if decision is Decision.ONAY_GEREKLI:
            approved = await approve(PendingPlan(tool=tool.name, spoken=_spoken(tool, values)))
            if not approved:
                return ToolResult(ok=False, error="kullanıcı onaylamadı")

        try:
            async with asyncio.timeout(tool.timeout_seconds):
                return await tool.handler(self._tools, values)
        except TimeoutError:
            # §8.2: zaman aşımı bir hata değil, modele geri beslenen bir sonuç.
            log.warning("tool zaman aşımı", tool=tool.name, seconds=tool.timeout_seconds)
            return ToolResult(ok=False, error=f"zaman aşımı ({tool.timeout_seconds} sn)")


def _spoken(tool: Tool, values: Mapping[str, object]) -> str:
    """§8.5 adım 3: yapılacak işlem ve argümanları açıkça okunur.

    Cümlenin kendisi tool'un yanında duruyor (`spec.Tool.confirm`), burada değil: hangi
    işlemin nasıl sorulacağını bilen taraf o dosya (Kural 9), ajan yalnızca soruyor.
    """
    return tool.confirmation(values)


def _assistant(call_text: str, produced: str | NativeCall) -> PromptMessage:
    """Çağrıyı taşıyan `assistant` mesajı — biçime göre metin ya da `tool_calls`.

    Yerel biçimde çağrı `content`'e **yazılmıyor**: yazıldığında model bir sonraki turda
    kendi geçmişinde düz metin bir çağrı görüyor ve onu kopyalıyor — ölçümde dört tur
    boyunca sesli cevap olarak `{"name": "volume", …}` üretti (`docs/faz-b-yerel.md`).
    """
    if isinstance(produced, NativeCall):
        return PromptMessage(role="assistant", content=call_text, tool_calls=(produced,))
    return PromptMessage(role="assistant", content=call_text)


def _correction(exc: CallParseError | ToolArgumentError) -> str:
    """§8.3'ün geri beslediği metin. `ToolArgumentError` `usage()`'ı üstünde taşıyor —
    modelin imzayı yeniden görmesi, hatayı görmesinden daha çok işe yarıyor."""
    if isinstance(exc, ToolArgumentError):
        return f"hata: {exc}\n{exc.usage}"
    return f"hata: {exc}"


def _feedback(result: ToolResult) -> str:
    """Modele geri beslenen biçim. `speech` değil `data` gidiyor (§9.1): biri kullanıcıya
    okunacak cümle, diğeri modelin üstüne akıl yürüteceği veri."""
    if not result.ok:
        return f"hata: {result.error}"
    return json.dumps(result.data or {}, ensure_ascii=False, sort_keys=True)

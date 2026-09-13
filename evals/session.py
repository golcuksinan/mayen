"""Oturum ölçümü: turlar sıra ile, geçmişi modelin kendi çıktısı yazıyor (Faz A/A2).

`uv run --env-file .env python -m evals.session --model <ad> --out docs/<ad>.md`

**Bugünkü kümelerin hiçbirinin ölçemediği şey.** `evals/runner.py`'nin her senaryosu
dondurulmuş bir geçmişe karşı tek turdur; `issues.md` #7'nin arızası ise turlar arası bir
sürüklenme — modelin çıktısı bir sonraki turun girdisi oluyor ve bellek onu işliyor. Bu
koşucu o döngüyü kapatıyor: geçici bir veritabanı, üretimin pencere kurucusu, üretimin
`Digest`'i, ve her tur bir öncekinin bıraktığı hâlin üstüne.

**Ölçülen sayı ikili değil, bir kırılma noktası:** kaçıncı turda ilk beklenen çağrı
atlandı, ve oturumun sonunda çağrı oranı ne. Tek bir yüzde bunu göstermez — arızanın
şekli baştan sona düz bir hata oranı değil, bir yerden sonra düşen bir eşik.

**`Digest` açık/kapalı bir kol.** Aynı senaryo iki kez koşuluyor ve fark, arka plan
belleğinin (özet + olgu çıkarımı) payıdır. Ölçümde `Digest`'in hiç koşmaması P27'nin
hatasının bir katman aşağısıydı (`docs/bellek-kirlenmesi.md` §3.1); bu kol onu kapatıyor.

**Mevcut tablolara karışmıyor** (P13). Eski kümeler belirlenimci ve öyle kalıyorlar;
buranın paydası tur, senaryo değil, ve raporu ayrı. Tekrar koşuları `--tekrar` ile
alınıyor: açgözlü örneklemede oturumun tamamı belirlenimci **olmalı** ve bu bir iddia
değil, `--tekrar 2` ile sınanabilen bir şey.

**Üretimden bilerek ayrıldığı iki yer, ikisi de rapora yazılıyor:**

1. **Tur başına en fazla bir çağrı.** Ajan döngüsü koşmuyor; ölçülen şey zincirin uzunluğu
   değil, ilk halkasının var olup olmadığı.
2. **Tool gövdeleri koşmuyor**, sonuçlar `evals/sessions.py`'de elle yazılı. Ağ, veritabanı
   ve makinenin ses seviyesi bir ölçümün içinde olmamalı.
"""

import argparse
import asyncio
import json
import sys
import tempfile
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import aclosing
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx

from evals.report import wilson
from evals.runner import MAX_TOKENS, _Attempt, _attempt
from evals.sessions import SESSIONS, SessionScenario, Turn
from mayen.adapters.errors import ServiceUnavailableError
from mayen.adapters.llamacpp import LlamaCppLLM
from mayen.adapters.llm import LLMClient, NativeCall, PromptMessage
from mayen.agent.calls import CallFormat, ToolCall
from mayen.agent.prompt import ContextBlock, build_messages, load_role, system_prompt
from mayen.config import Config, ConfigError, load
from mayen.data import clock
from mayen.data.db import Database
from mayen.data.migrate import migrate
from mayen.data.repositories.conversation import MessageRepository, SummaryRepository
from mayen.data.repositories.facts import FactRepository
from mayen.data.repositories.people import PeopleRepository
from mayen.main import (
    CALL_FORMAT,
    DIGEST_BATCH,
    DIGEST_KEEP_RECENT,
    DIGEST_MAX_TOKENS,
    MAX_CORRECTIONS,
    MAX_FACTS,
    MAX_HISTORY_MESSAGES,
    RESERVED_OUTPUT_TOKENS,
)
from mayen.memory.digest import Digest
from mayen.memory.recall import Recall
from mayen.memory.window import ContextWindow
from mayen.policy.authority import Authority, Identity
from mayen.tools.catalog import builtin_registry
from mayen.tools.grammar import PROSE_GRAMMAR
from mayen.tools.registry import Registry
from mayen.tools.schema import schemas
from mayen.tools.spec import ToolArgumentError

TIMEOUT_SECONDS = 300.0

START = "2026-08-16T11:00:00Z"
"""Bağlam bloğunun dondurulmuş başlangıcı — o günün kendisi (Pazar).

Gerçek saat kullanılsaydı ölçüm takvimle birlikte kayardı: `otu-01`'in ders beklentisi
"bugün Pazar" varsayıyor ve bir hafta sonra koşan aynı senaryo başka bir sınav olurdu.
`evals/scenarios.py:NOW`'un aynı gerekçesi."""

TURN_SECONDS = 30
"""İki tur arasında bağlam bloğunun ilerlediği süre. Sabit ve küçük: saatin **ilerlediği**
görünmeli (gerçek konuşma altmış sekiz dakika sürdü) ama gün değişmemeli."""


@dataclass(frozen=True, slots=True)
class TurnResult:
    index: int
    user: str
    expected: str | None
    call: ToolCall | None
    answer: str
    prompt_tokens: int
    summary_chars: int
    facts: int
    errors: tuple[str, ...] = ()
    """Bu turda düşen servis çağrıları (`issues.md` #2). Boş değilse tur **eksik** ölçüldü
    ve rapor bunu ayrı bir satırda yazıyor: yutulmuş bir kesinti, modelin hatası gibi
    okunurdu (Kural 13, `runner.run_all`'ın aynı gerekçesi)."""

    @property
    def hit(self) -> bool:
        """Beklenen tool çağrıldı mı — beklenmiyorsa "hiç çağrı gelmedi mi"."""
        if self.expected is None:
            return self.call is None
        return self.call is not None and self.call.name == self.expected


@dataclass(frozen=True, slots=True)
class SessionResult:
    scenario_id: str
    call_format: CallFormat
    digest: bool
    turns: tuple[TurnResult, ...]
    digest_errors: int = 0
    """Düşen özetleme işi sayısı. Üretimde de olabilen bir şey: iş boştaki bir fırsatta
    koşuyor ve düşerse bir sonraki fırsatta aynı yığın baştan işleniyor."""
    native: bool = False
    """Çağrı **yerel biçimde** mi istendi: katalog `tools` alanında şema olarak, çağrıyı
    sunucu ayrıştırıyor (`mayen/tools/schema.py`). `CallFormat`'a üçüncü bir değer
    eklenmedi — bu bir ölçüm kolu, alınmış bir karar değil; üretimi seçen satır hâlâ
    `main.py:CALL_FORMAT`."""

    @property
    def wanted(self) -> tuple[TurnResult, ...]:
        """Çağrı beklenen **ve ölçülebilmiş** turlar. Düşen tur hiçbir paydaya girmiyor:
        yanlış sayılsaydı model servisin kopmasından sorumlu tutulurdu (Kural 14)."""
        return tuple(t for t in self.turns if t.expected is not None and not t.errors)

    @property
    def called(self) -> int:
        return sum(t.hit for t in self.wanted)

    @property
    def first_missed(self) -> int | None:
        """İlk atlanan beklenen çağrının tur numarası. Arızanın **şekli** bu sayıda:
        bir oran "yarısını kaçırdı" der, bu sayı "on ikinci turdan sonra hiç çağırmadı"
        der ve ikisi aynı şey değil."""
        return next((t.index for t in self.wanted if not t.hit), None)

    @property
    def failed_turns(self) -> int:
        return sum(bool(t.errors) for t in self.turns)

    @property
    def over_called(self) -> int:
        """Çağrı beklenmezken çağrılan turlar. Negatif kontrol: yalnızca çağrı oranına
        bakan bir ölçüm, her tura tool çağıran bir modeli mükemmel gösterirdi."""
        return sum(
            t.expected is None and t.call is not None and not t.errors for t in self.turns
        )


async def _retry[T](what: str, call: Callable[[], Awaitable[T]]) -> T:
    """Bir servis çağrısını bir kez daha dener (`runner.run_all`'ın kuralı).

    `issues.md` #2 bu koşunun içinde görüldü: `llama-server` ölmeden tek bir bağlantıyı
    düşürdü ve yirmi dakikalık bir oturum ölçümü orada bitti. Yeniden denenen şey bir
    üretim değil, **baştan bir istek** — yarısı tüketilmiş bir akış tekrar oynatılmıyor
    (P12). Tükendiğinde hata yine yükseliyor; çağıran onu tura yazıyor (Kural 13).
    """
    for attempt in (1, 2):
        try:
            return await call()
        except ServiceUnavailableError as error:
            print(f"  {what} düştü ({attempt}/2): {error}", file=sys.stderr)
            if attempt == 2:
                raise
    raise AssertionError("erişilemez")


async def run_session(
    config: Config,
    llm: LLMClient,
    registry: Registry,
    scenario: SessionScenario,
    *,
    call_format: CallFormat,
    digest_on: bool,
    native: bool = False,
) -> SessionResult:
    """Senaryoyu baştan sona koşar. Her tur `turn/runner.py:_run`'ın sırasını izliyor."""
    system = _system(config, registry, native=native)
    tools = schemas(registry) if native else None
    identity = Identity(
        authority=Authority.SAHIP if config.assume_owner else Authority.TANINMAYAN
    )
    started = clock.parse(START)
    results: list[TurnResult] = []
    digest_errors = 0
    with (
        tempfile.TemporaryDirectory(prefix="mayen-session-") as tmp,
        Database(Path(tmp) / "session.db") as db,
    ):
        migrate(db)
        messages = MessageRepository(db)
        summaries = SummaryRepository(db)
        facts = FactRepository(db)
        memory = ContextWindow(
            llm=llm,
            messages=messages,
            summaries=summaries,
            recall=Recall(facts, PeopleRepository(db), max_facts=MAX_FACTS),
            reserved_output=RESERVED_OUTPUT_TOKENS,
            max_messages=MAX_HISTORY_MESSAGES,
        )
        digest = Digest(
            llm=llm,
            messages=messages,
            summaries=summaries,
            facts=facts,
            keep_recent=DIGEST_KEEP_RECENT,
            batch_size=DIGEST_BATCH,
            max_tokens=DIGEST_MAX_TOKENS,
        )
        for index, turn in enumerate(scenario.turns, 1):
            now = (started + timedelta(seconds=TURN_SECONDS * (index - 1))).strftime(
                clock.FORMAT
            )
            try:
                results.append(
                    await _run_turn(
                        llm,
                        registry,
                        memory,
                        turn,
                        index=index,
                        now=now,
                        system=system,
                        identity=identity,
                        call_format=call_format,
                        tools=tools,
                    )
                )
            except ServiceUnavailableError as error:
                # Tur ölçülemedi, oturum sürüyor (Kural 13, `runner.run_all`'ın gerekçesi).
                # Geçmişe asistan satırı yazılmadı: olmayan bir cevabı kaydetmek, sonraki
                # turların gördüğü konuşmayı uydurmak olurdu.
                print(f"  tur {index} ölçülemedi: {error}", file=sys.stderr)
                results.append(_failed_turn(index, turn, str(error)))
            if digest_on:
                # Üretimde bu iş turun **arasında**, boşta koşuyor (Kural 11). Düşerse
                # oturum sürüyor: üretimde de bir sonraki boşlukta aynı yığın baştan
                # işlenir, yani düşen bir özetleme oturumu bitiren bir olay değil.
                try:
                    await _retry("özetleme", digest.run)
                except ServiceUnavailableError:
                    digest_errors += 1
            latest = summaries.latest()
            results[-1] = replace(
                results[-1],
                summary_chars=len(latest.content) if latest else 0,
                facts=len(facts.list_all()),
            )
    return SessionResult(
        scenario_id=scenario.id,
        call_format=call_format,
        digest=digest_on,
        native=native,
        turns=tuple(results),
        digest_errors=digest_errors,
    )


def _failed_turn(index: int, turn: Turn, error: str) -> TurnResult:
    """Ölçülemeyen tur. Hiçbir orana girmiyor ama satırı duruyor (Kural 13): yazılmasaydı
    payda sessizce küçülür ve rapor eksikliğini gizlerdi."""
    return TurnResult(
        index=index,
        user=turn.user,
        expected=turn.expected,
        call=None,
        answer="",
        prompt_tokens=0,
        summary_chars=0,
        facts=0,
        errors=(error,),
    )


async def _run_turn(
    llm: LLMClient,
    registry: Registry,
    memory: ContextWindow,
    turn: Turn,
    *,
    index: int,
    now: str,
    system: str,
    identity: Identity,
    call_format: CallFormat,
    tools: Sequence[dict[str, object]] | None = None,
) -> TurnResult:
    turn_id = str(uuid.uuid4())
    context = ContextBlock(now=now, speaker=identity.authority.value)
    window = await memory.build(
        fixed_text=f"{system}\n{context.render()}\n{turn.user}",
        person_id=identity.person_id,
    )
    context = replace(context, facts=window.facts)
    # Kayıt pencereden **sonra**: aksi hâlde kullanıcının cümlesi geçmişte de görünürdü
    # (`turn/runner.py`'nin gerçek modelde görülmüş hatası).
    memory.record(turn_id, "user", turn.user, person_id=identity.person_id)
    prompt = build_messages(
        system,
        context=context,
        user=turn.user,
        summary=window.summary,
        history=window.history,
    )
    if tools is not None:
        # Geçmişteki çağrılar metinden `tool_calls`'a; işaret modele hiç gitmiyor.
        prompt = tuple(_native_history(prompt))
    tokens = await llm.count_tokens("\n".join(m.content for m in prompt))
    errors: list[str] = []
    if tools is None:
        attempt = await _retry(
            f"tur {index} üretimi",
            lambda: _attempt(
                registry, llm, call_format, prompt, max_corrections=MAX_CORRECTIONS
            ),
        )
    else:
        # Yerel biçim `LLMClient` arayüzünde değil (bkz. `stream_native`): sahte bir
        # istemciyle koşulamaz ve bu kol zaten gerçek sunucuyu ölçüyor.
        if not isinstance(llm, LlamaCppLLM):
            raise TypeError("yerel biçim yalnızca LlamaCppLLM ile ölçülebilir")
        native_llm = llm
        attempt = await _retry(
            f"tur {index} üretimi",
            lambda: _native_attempt(registry, native_llm, prompt, tools),
        )
    if attempt.call is None:
        answer = attempt.output
    else:
        # Yerel kolda çağrının metni yok — şablon taşıyor; geçmişe ve geri beslemeye
        # giden satır defterden kuruluyor (`_call_line`).
        call_line = attempt.output if tools is None else _call_line(attempt.call)
        called = attempt.call
        try:
            answer = await _retry(
                f"tur {index} yanıtı",
                lambda: (
                    _answer(llm, attempt.messages, call_line, turn)
                    if tools is None
                    else _native_answer(native_llm, attempt.messages, called, turn, tools)
                ),
            )
        except ServiceUnavailableError as error:
            # Çağrı ölçüldü — bu ölçümün asıl sayısı o. Yanıt yok, ve yokluğu yazılıyor.
            answer = ""
            errors.append(str(error))
        # Üretimin dizisi birebir (`turn/runner.py`): çağrı `assistant`, sonuç `tool`.
        # Senaryonun elle yazılı sonucu burada iki kez kullanılıyor — modele geri
        # beslenirken ve geçmişe yazılırken — çünkü üretimde de aynı metin ikisine gidiyor.
        memory.record(turn_id, "assistant", call_line)
        memory.record(turn_id, "tool", _fed(turn))
    if answer:
        memory.record(turn_id, "assistant", answer)
    return TurnResult(
        index=index,
        user=turn.user,
        expected=turn.expected,
        call=attempt.call,
        answer=answer,
        prompt_tokens=tokens,
        summary_chars=0,
        facts=0,
        errors=tuple(errors),
    )


async def _native_attempt(
    registry: Registry,
    llm: LlamaCppLLM,
    messages: Sequence[PromptMessage],
    tools: Sequence[dict[str, object]],
) -> _Attempt:
    """Yerel biçimde tek üretim (2026-08-16, Faz B/2).

    `_attempt`'in kardeşi ve kasten daha kısa: **düzeltme döngüsü yok.** Çağrıyı sunucu
    ayrıştırıyor ve argümanlar şemayla kısıtlı, yani `_attempt`'in düzelttiği hata
    sınıfı (bozuk sözdizimi) burada taşımanın altında kalıyor. Kalan tek doğrulama
    defterin kendisi: ad kayıtlı mı, argümanlar geçerli mi. Geçersizse çağrı **düşmüş**
    sayılıyor ve `failures`'a yazılıyor — düzeltme turu eklemek, iki kolu farklı sayıda
    üretimle karşılaştırmak olurdu.

    **Metin ile çağrı aynı yanıtta gelebilir** ve ölçümün asıl konusu bu: bugünkü
    gramerde model ya konuşuyor ya çağırıyor, ve ikisini birden isteyince çağrıyı düz
    metin içinde taklit ediyor (`mayen/tools/schema.py`). Burada ikisi de kaydediliyor;
    `output` modelin söylediği söz, `call` gerçekten koşan çağrı.

    Tur başına **bir** çağrı ölçülüyor (modül başlığı): sunucu birden çok çağrı
    döndürürse ilki alınıyor ve gerisi `failures`'a yazılıyor, sessizce atılmıyor.
    """
    started = time.monotonic()
    ttft = 0.0
    text: list[str] = []
    calls: list[NativeCall] = []
    stream = llm.stream_native(messages, tools=tools, max_tokens=MAX_TOKENS)
    async with aclosing(stream) as events:
        async for event in events:
            if not ttft:
                ttft = time.monotonic() - started
            if isinstance(event, NativeCall):
                calls.append(event)
            else:
                text.append(event)

    failures = [f"fazladan çağrı: {c.name}" for c in calls[1:]]
    call: ToolCall | None = None
    unknown_tool = 0
    unknown_argument = 0
    if calls:
        # §17.1'in uyarısı burada da geçerli ve şekli değişiyor: gramerde uydurulan ad
        # **üretilemezdi**, şemada üretilebilir — sunucu şemayı zorlamayabilir. Yani bu
        # iki sayaç yerel kolda ilk kez gerçekten modeli ölçüyor.
        try:
            registry.get(calls[0].name).validate(_as_text(calls[0].arguments))
            call = ToolCall(name=calls[0].name, arguments=calls[0].arguments)
        except KeyError:
            unknown_tool += 1
            failures.append(f"bilinmeyen tool: {calls[0].name}")
        except ToolArgumentError as exc:
            unknown_argument += 1
            failures.append(str(exc).splitlines()[0])
    return _Attempt(
        messages=messages,
        output="".join(text),
        call=call,
        unknown_tool=unknown_tool,
        unknown_argument=unknown_argument,
        corrections=0,
        failures=failures,
        ttft=ttft,
    )


def _as_text(arguments: Mapping[str, Any]) -> dict[str, str]:
    """Şemadan gelen tipli değerleri `Tool.validate`'in beklediği metne çevirir.

    `validate` §8.3'ün metin biçimlerinin ürünü: her değer metin olarak geliyor ve
    tipe **o** çeviriyor. Yerel biçimde tipi şablon zaten veriyor, yani `{"level": 40}`
    bir `int`. İki taraftan biri esnetilecekti; esneyen taraf ölçüm oldu, çünkü
    `validate` üretimin tek doğrulama noktası ve bir ölçüm kolu için gevşetilmesi
    üretimi ölçüme uydurmak olurdu. Liste virgülle birleşiyor — `_coerce`'ün ayırdığı yer.
    """
    out = {}
    for name, value in arguments.items():
        out[name] = (
            ",".join(str(item) for item in value) if isinstance(value, list) else str(value)
        )
    return out


_CALL_MARK = "\x00yerel-çağrı "
"""Geçmişteki bir asistan satırının çağrı olduğunu söyleyen işaret.

Geçmiş veritabanından **metin** olarak geliyor (`data/repositories/conversation.py`);
`tool_calls` alanı orada yok ve ölçüm için şema değiştirilmiyor. İşaret bu yüzden var:
satır yazılırken konuyor, isteğe çevrilirken sökülüp `PromptMessage.tool_calls`'a
dönüyor, yani **modele hiç metin olarak gitmiyor**. Yazdırılamayan bir karakterle
başlıyor ki modelin ürettiği hiçbir cevapla karışmasın.

Bu bir ölçüm iskelesi. Yerel biçim üretime alınırsa doğrusu çağrıyı satırın yanında
saklamak olur — o zaman `data`'nın şeması da değişir."""


def _call_line(call: ToolCall) -> str:
    """Yerel kolda geçmişe yazılan `assistant` satırı (işaretli, bkz. `_CALL_MARK`).

    Üretimin CLI kolunda oraya modelin **kendi ürettiği** çağrı metni gidiyor; yerel
    biçimde model metin üretmiyor, çağrıyı şablon taşıyor. Geçmişte bir iz kalmalı,
    yoksa sonuç (`tool` satırı) sebepsiz duruyor ve iki kol farklı **geçmişlerle**
    koşardı — ölçülen tek değişken çağrı arayüzü olmalı.
    """
    body = json.dumps(
        {"name": call.name, "arguments": dict(call.arguments)}, ensure_ascii=False
    )
    return _CALL_MARK + body


def _native_history(messages: Sequence[PromptMessage]) -> list[PromptMessage]:
    """İşaretli asistan satırlarını `tool_calls` taşıyan mesajlara çevirir.

    İlk koşuda bu yoktu ve ölçüm kirlendi (`docs/faz-b-yerel.md`): çağrı geçmişte düz
    metin olarak durunca model onuncu turdan sonra biçimi **kopyaladı** ve dört turda
    cevap olarak `{"name": "volume", "arguments": {...}}` üretti. Model geçmişte kendi
    ürettiği biçimi görmeli — yoksa ölçülen şey çağrı arayüzü değil, geçmişin biçimi olur.
    """
    out = []
    for message in messages:
        if message.role == "assistant" and message.content.startswith(_CALL_MARK):
            payload = json.loads(message.content[len(_CALL_MARK) :])
            call = NativeCall(name=payload["name"], arguments=payload["arguments"])
            out.append(PromptMessage("assistant", "", (call,)))
        else:
            out.append(message)
    return out


def _fed(turn: Turn) -> str:
    """Senaryonun tool sonucu, `agent/loop.py:_feedback`'in başarı dalıyla aynı biçimde."""
    return json.dumps(turn.result, ensure_ascii=False, sort_keys=True)


async def _answer(
    llm: LLMClient, messages: Sequence[PromptMessage], call_output: str, turn: Turn
) -> str:
    """Tool sonucu geri beslenip yanıt üretilir. Gramer `PROSE_GRAMMAR`: tur başına bir
    çağrı ölçülüyor (bkz. modül başlığı) ve ikinci bir çağrı dalı açık kalsaydı, ölçülen
    şey zincirin uzunluğu olurdu."""
    chunks = [
        chunk
        async for chunk in llm.stream(
            [
                *messages,
                PromptMessage("assistant", call_output),
                # Rol `tool`, `user` değil — `agent/loop.py`'nin geri beslediği biçimin
                # aynısı. Ayrışmışlardı: ölçüm `[tool sonucu]` etiketiyle bir `user`
                # mesajı kuruyordu, üretim etiketsiz bir `tool` mesajı. Ölçülen önek
                # üretimin kurmadığı bir önekti (P27'nin dersi).
                PromptMessage("tool", _fed(turn)),
            ],
            grammar=PROSE_GRAMMAR,
            max_tokens=MAX_TOKENS,
        )
    ]
    return "".join(chunks)


async def _native_answer(
    llm: LlamaCppLLM,
    messages: Sequence[PromptMessage],
    call: ToolCall,
    turn: Turn,
    tools: Sequence[dict[str, object]],
) -> str:
    """Yerel kolun yanıt adımı: çağrı `tool_calls`, sonuç `tool` rolünde geri besleniyor.

    `_answer`'ın kardeşi, iki farkla. Gramer yok — `PROSE_GRAMMAR` burada `tools`'u ezer
    ve şablonun kendi biçimini bozardı. İkinci çağrı bu yüzden dilbilgisel olarak
    engellenemiyor; gelirse **metni** alınıp çağrı yok sayılıyor, çünkü ölçülen şey tur
    başına bir çağrı (modül başlığı). CLI kolunda aynı kısıtı gramer koyuyor; ikisinin
    sonucu aynı, yolu farklı ve bu fark rapora yazılı.
    """
    history = [
        *messages,
        PromptMessage("assistant", "", (NativeCall(name=call.name, arguments=call.arguments),)),
        PromptMessage("tool", _fed(turn)),
    ]
    stream = llm.stream_native(history, tools=tools, max_tokens=MAX_TOKENS)
    text = []
    async with aclosing(stream) as events:
        async for event in events:
            if isinstance(event, str):
                text.append(event)
    return "".join(text)


def _system(config: Config, registry: Registry, *, native: bool = False) -> str:
    """Sistem promptu. Yerel kolda **katalog ve çağrı sözdizimi çıkıyor**.

    İkisini de şablon `tools` alanından yerleştiriyor; bırakılsalardı model aynı defteri
    iki kez, iki farklı sözdizimiyle görürdü — §9.1'in "ikinci, bağımsız metin" hatası.
    Kalan: rol metni + dil kuralı, aynı sırayla. Sondajın (`docs/faz-b-sondaj-yerel.md`)
    kurduğu öneğin aynısı.
    """
    if config.role_path is None:
        raise ConfigError("Rol dosyası verilmedi: MAYEN_ROLE_PATH")
    rule = load_role(config.language_rule_path) if config.language_rule_path else None
    if native:
        parts = [load_role(config.role_path)]
        if rule is not None:
            parts.append(rule)
        return "\n\n".join(parts)
    return system_prompt(
        registry, CALL_FORMAT, role=load_role(config.role_path), language_rule=rule
    )


def render(model: str, runs: Sequence[SessionResult]) -> str:
    """Rapor. Her koşu kendi bölümüyle: turların sırası ölçülen şeyin kendisi ve
    ortalamaya eritilirse kırılma noktası kaybolur."""
    lines = [
        "# Oturum ölçümü",
        "",
        f"Model: `{model}`. Turlar **sıra ile** koşuluyor; geçmişi modelin kendi çıktısı"
        " yazıyor ve turların arasında üretimin `Digest`'i geçici bir veritabanına karşı"
        " çalışıyor.",
        "",
        "**Paydası tur, senaryo değil** — bu tablo `docs/faz*-olcum.md`'nin tablolarıyla"
        " karşılaştırılamaz (P13: eski kümeler belirlenimci ve tek turluk).",
        "",
        "Tur başına en fazla bir çağrı ölçülüyor ve tool gövdeleri koşmuyor; sonuçlar"
        " `evals/sessions.py`'de elle yazılı.",
        "",
        "| koşu | beklenen çağrı | gelen [%95] | ilk atlanan tur | gereksiz çağrı |"
        " son özet (karakter) | son olgu | düşen |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in runs:
        wanted = len(run.wanted)
        low, high = wilson(run.called, wanted)
        missed = run.first_missed
        last = run.turns[-1]
        dropped = run.failed_turns + run.digest_errors
        lines.append(
            f"| {_label(model, run)} | {wanted} |"
            f" {run.called} ({run.called / wanted:.0%}) [{low:.0%}–{high:.0%}] |"
            f" {missed if missed is not None else '—'} | {run.over_called} |"
            f" {last.summary_chars} | {last.facts} | {dropped} |"
        )
    if any(run.failed_turns or run.digest_errors for run in runs):
        lines += [
            "",
            "**`düşen` sıfır değil:** servis en az bir kez koptu (`issues.md` #2). Düşen"
            " turun çağrısı ölçülemedi ve geçmişine hiçbir cevap yazılmadı, yani o"
            " oturumun geri kalanı üretimdekinden **farklı** bir konuşmanın üstüne koştu."
            " Sayı sıfır değilse koşu tekrarlanmalı.",
        ]
    for run in runs:
        lines += ["", f"## {_label(model, run)}", "", *_turn_table(run)]
    return "\n".join(lines)


def _label(model: str, run: SessionResult) -> str:
    # Metin kolu adında `metin(...)` taşıyor: `CALL_FORMAT` yerelken iki kol da "yerel"
    # yazıyordu ve rapor kendi kollarını ayırt edilemez kılıyordu.
    biçim = "yerel" if run.native else f"metin({run.call_format.value})"
    return (
        f"{model} × {biçim} × {run.scenario_id}"
        f" × özetleme({'açık' if run.digest else 'kapalı'})"
    )


def _turn_table(run: SessionResult) -> list[str]:
    lines = [
        "| # | kullanıcı | beklenen | gelen | önek jetonu | özet | olgu | yanıt |",
        "|---:|---|---|---|---:|---:|---:|---|",
    ]
    for turn in run.turns:
        got = turn.call.name if turn.call else "—"
        mark = "" if turn.hit else " ⚠"
        answer = turn.answer.strip().replace("|", "\\|").replace("\n", " ")[:90]
        lines.append(
            f"| {turn.index} | {turn.user} | {turn.expected or '—'} | {got}{mark} |"
            f" {turn.prompt_tokens} | {turn.summary_chars} | {turn.facts} | {answer} |"
        )
    return lines


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evals.session", description="Oturum ölçümü: turlar sıra ile"
    )
    parser.add_argument("--model", required=True, help="Rapora yazılacak model adı")
    parser.add_argument("--out", type=Path, help="Raporun yazılacağı dosya")
    parser.add_argument(
        "--tekrar",
        type=int,
        default=1,
        help="Aynı koşunun kaç kez tekrarlanacağı. Açgözlü örneklemede oturum belirlenimci"
        " olmalı; bu bayrak onu sınamak için var",
    )
    parser.add_argument(
        "--ozetlemesiz",
        dest="no_digest",
        action="store_true",
        help="Yalnızca `Digest` kapalı kol koşulsun",
    )
    parser.add_argument(
        "--metin-kolu",
        dest="text_arm",
        action="store_true",
        help="Yerel kolun yanına bir de metin kolu koş. **Yalnızca `CALL_FORMAT` bir metin"
        " biçimiyken anlamlı:** §19.1 onu `YEREL` yaptığından beri metin kolu `parse()`'a"
        " yerel biçim veriyor, o da `calls.py:145`'te 'kodun hatası' diyor — yani kol çağrı"
        " üretmiyor ve skoru bir ölçüm değil. Varsayılan olarak kapalı, o yüzden",
    )
    args = parser.parse_args(argv)

    try:
        config = load()
    except ConfigError as error:
        print(f"yapılandırma okunamadı: {error}", file=sys.stderr)
        return 1
    registry = builtin_registry(config)
    arms = [False] if args.no_digest else [True, False]
    async with httpx.AsyncClient(base_url=config.llm_url, timeout=TIMEOUT_SECONDS) as http:
        llm = LlamaCppLLM(http, name=args.model)
        if not await llm.health():
            print(f"LLM servisi yanıt vermiyor: {config.llm_url}", file=sys.stderr)
            return 1
        runs = []
        # İki kol aynı koşuda, ayrı dosyalarda değil: aynı gün aynı sunucuya koştukları
        # ancak tek bir raporda görülebilir (P27'nin `--onek` gerekçesi).
        # Üretimin biçimi varsayılan, ikinci kol istenirse eklenir. Eskiden tersiydi:
        # metin kolu daima koşuyordu ve `--yerel` onun yanına yereli ekliyordu. §19.1
        # `CALL_FORMAT`'ı `YEREL` yapınca varsayılan kol ölçüm olmaktan çıktı.
        native_only = CALL_FORMAT is CallFormat.YEREL
        formats = [native_only] if not args.text_arm else [False, True]
        for scenario in SESSIONS:
            for digest_on in arms:
                for native in formats:
                    for repeat in range(args.tekrar):
                        print(
                            f"koşuluyor: {scenario.id}"
                            f" biçim={'yerel' if native else f'metin({CALL_FORMAT.value})'}"
                            f" özetleme={'açık' if digest_on else 'kapalı'}"
                            f" ({repeat + 1}/{args.tekrar})",
                            file=sys.stderr,
                        )
                        runs.append(
                            await run_session(
                                config,
                                llm,
                                registry,
                                scenario,
                                call_format=CALL_FORMAT,
                                digest_on=digest_on,
                                native=native,
                            )
                        )
    report = render(args.model, runs)
    if args.out is None:
        print(report)
    else:
        args.out.write_text(report, encoding="utf-8")
        print(f"rapor yazıldı: {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

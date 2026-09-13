"""Faz 0 koşucusu: bir senaryo × bir çağrı biçimi × bir model (§18).

**Prompt düzeni §8.1'in kendisi.** Sabit önek (çağrı yönergesi + katalog) `system`
mesajıdır ve senaryodan senaryoya baytı baytına aynıdır; değişken içerik — dondurulmuş
tarih/saat — bağlam bloğu olarak **en sona**, kullanıcı turunun başına yazılır. Ayrı bir
mesaj yapılmadı: rol kümesinde bağlam bloğuna karşılık gelen bir rol yok ve arka arkaya
iki `user` mesajı bazı sohbet şablonlarını bozuyor. Önemli olan kural korunuyor — önek
sabit, değişken içerik sonda.

**Kendini düzeltme turu ölçülüyor, gizlenmiyor** (§8.3). Geçersiz çağrıda modele
`usage()` geri besleniyor ve tur sayılıyor. Sınır bir ölçüm parametresi, bir doküman
kararı değil: §19'da sayı yok, o yüzden varsayılan küçük tutuldu ve rapora yazılıyor.

**Karşılaştırma birebir — tek istisnası cümle sonu noktalaması.** Türkçe'de
`.lower()`/`.upper()` `I`/`ı` üzerinde yanlış çalışır, o yüzden harf katlaması yok ve
olmayacak. Atılan tek şey en sondaki `.!?`: kullanıcının cümlesini bitiren nokta argümanın
içeriği değil ve onu hata saymak modelin doğrusunu yanlış raporlamaktı (bkz. `_comparable`).
Beklentinin tek anlamlı olmadığı yerde küme zaten `ANY` yazıyor.

**Üçüncü halüsinasyon sayacı: desteksiz sayı.** §17.1'in üçüncüsü — tool sonucunda
bulunmayan bir bilgiyi yanıtta iddia etme. Doğru çağrıyı üreten ve `Scenario.result` taşıyan
senaryolarda tool sonucu modele geri besleniyor, yanıt tool dalı **kapalı** gramerle
üretiliyor ve yanıttaki her sayı iki kaynağa karşı aranıyor: tool sonucu ve kullanıcı turu
(bağlam bloğu dâhil). İkisinde de geçmeyen bir sayı desteksiz iddiadır.

**Neden yalnızca sayılar.** Serbest bir cümlenin "sonuçta var mıydı" sorusunu mekanik
olarak cevaplayan tek şey sayılar; gerisi bir hakem modeli ister ve hakemin kendi
halüsinasyonu ölçüme karışır. Sayaç bu yüzden dar ve raporda dar adıyla duruyor: sayısal
iddia. Sıfır çıkması "hiç halüsinasyon yok" demek değil, "ölçülen dilimde yok" demek
(Kural 14).

**Çağrı üretilmeyen senaryonun yanıtı da kaydediliyor** (P26). 2026-08-13'e kadar yanıt
turu yalnızca çağrı **doğru** üretildiğinde koşuyordu; yani modelin iddiaları sadece
iddianın desteklendiği durumda inceleniyordu ve üretimdeki asıl hata — hiç çağrı yapmadan
"not eklendi" demek — ölçümün göremediği yerde kalıyordu. Artık çağrısız çıktı `answer`'a
yazılıyor, ama `answer_graded` `False`: kanıt toplanıyor (Kural 13), ölçülmeyen şeye sayı
verilmiyor (Kural 14).

**Dördüncü sayaç: desteksiz alıntı.** Sayının eşi — yanıtta tırnak içinde geçip ne tool
sonucunda ne kullanıcı turunda ne de geçmişte bulunan metin. `issues.md` #3'ün uydurması
tırnak içinde bir listeydi. Tırnaksız serbest cümle hâlâ kapsam dışı.

**Tool gövdeleri koşulmuyor**, hazır sonuçlar besleniyor: ağ ve veritabanı ölçümü
belirlenimci olmaktan çıkarırdı ve ölçülen şey tool'un doğruluğu değil.

**İkinci adım ölçülüyor** (P25.2). `Scenario.step2` varsa sonuç geri besleniyor ve model
bir kez daha *tool* grameriyle üretiyor; ölçülen şey ikinci çağrının gelip gelmediği ve
argümanının sonuçtan okunup okunmadığı. `PROSE_GRAMMAR` kullanılmıyor: negatif kontrol
satırlarında doğru cevap "çağrı yok" ve o dalı gramerle kapatmak, ölçülmek istenen hatayı
üretilemez kılardı. Yanıt turu ile ikinci adım birbirini dışlar — bkz. `Scenario.step2`.
"""

import json
import re
import time
from collections.abc import Sequence
from contextlib import aclosing
from dataclasses import dataclass, field
from enum import StrEnum

from evals.scenarios import NOW, ExpectedCall, Kind, Scenario
from mayen.adapters.errors import ServiceUnavailableError
from mayen.adapters.llm import LLMClient, NativeCall, PromptMessage
from mayen.agent.calls import (
    CallFormat,
    CallParseError,
    ToolCall,
    UnknownArgumentError,
    UnknownToolError,
    from_native,
    instructions,
    is_call,
    parse,
)
from mayen.agent.prompt import ContextBlock, build_messages
from mayen.agent.prompt import system_prompt as agent_system_prompt
from mayen.obs.log import get_logger
from mayen.tools.grammar import PROSE_GRAMMAR, cli_grammar, json_grammar
from mayen.tools.prompt import catalog_text
from mayen.tools.registry import Registry
from mayen.tools.schema import schemas
from mayen.tools.spec import ToolArgumentError

log = get_logger(__name__)

MAX_CORRECTIONS = 2
"""Kendini düzeltme turu tavanı. §19'da sayı yok; bu bir ölçüm parametresi ve rapora
yazılıyor. Sonsuz bırakmak, bozuk bir modelin ölçümü süresiz kilitlemesi demekti."""

MAX_TOKENS = 256
"""Tek bir çağrı ya da kısa bir yanıt bunun çok altında kalır; tavan yalnızca kaçak
üretimi durdurmak için."""


class Context(StrEnum):
    """Senaryonun geçmiş uzunluğu kovası. Rapor ikisini ayrı gösteriyor: aynı tuzak kısa
    ve uzun geçmişte farklı sonuç veriyorsa, tek bir ortalama bunu gizler."""

    YOK = "geçmişsiz"
    KISA = "kısa geçmiş"
    UZUN = "uzun geçmiş"


LONG_CONTEXT_TOKENS = 200
"""Kaç jetondan sonrası "uzun bağlam" sayılıyor (P27).

**Bir rapor kovası, sistemde bir eşik değil** — hiçbir kod bu sayıya bakarak davranış
değiştirmiyor, ve §19'da bağlam uzunluğuna dair bir sayı yok. Bir ölçüm parametresi, yani
`MAX_CORRECTIONS` gibi: gerekçesi yazılı ve rapora giriyor.

**Neden tur değil jeton.** `LONG_HISTORY = 4` "uzun"u 5 turluk, ~247 karakterlik bir blok
olarak tanımlıyordu ve bu ad yanıltıcıydı: modele giden şey tur değil jeton. Sayan taraf
sunucunun kendi sayacı (Kural 10); tahmin edilmiyor.

Değer, ölçülen iki şeklin arasına düşecek şekilde seçildi: `HISTORY_SCENARIOS`'un beş
turluk blokları bunun altında, `MEMORY_SCENARIOS`'un yirmi turluk pencereleri üstünde
kalıyor. Rapor ayrıca kovanın **gerçek** doluluğunu `n_ctx` yüzdesi olarak yazıyor, yani
eşik yanlış seçilmişse okuyan görüyor.
"""


def context_of(scenario: Scenario, tokens: int) -> Context:
    """Senaryonun bağlam kovası. `tokens`: öneğin değişken kısmının jeton sayısı."""
    if not scenario.history:
        return Context.YOK
    return Context.UZUN if tokens >= LONG_CONTEXT_TOKENS else Context.KISA


class Prefix(StrEnum):
    """Ölçümün hangi öneği kurduğu (P27).

    **İkisi de var, biri diğerinin yerine geçmiyor.** `ÖLÇÜM` bugüne kadarki bütün
    raporların öneği; baytı baytına korunuyor, yoksa `docs/faz2-olcum.md` ve `faz3-*`
    karşılaştırılamaz hâle gelirdi (P25.2'nin kuralı). `ÜRETİM` ise `turn/runner.py`'nin
    modele gerçekten gönderdiği dizi — rol metni, `[özet]` bloğu, olgular ve
    `ContextBlock.render()` dâhil. İkisinin farkı P27'nin ölçtüğü şeyin kendisi.
    """

    OLCUM = "ölçüm öneği"
    URETIM = "üretim öneği"


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Tek koşunun tüm ölçülenleri. Sayılar burada toplanmaz — rapor toplar."""

    scenario_id: str
    kind: Kind
    context: Context
    call_format: CallFormat
    model: str
    output: str
    call: ToolCall | None
    tool_correct: bool
    arguments_correct: bool | None
    """Tool yanlışsa ya da düz metin bekleniyorsa argüman doğruluğu tanımsızdır."""
    unknown_tool: int
    unknown_argument: int
    corrections: int
    tokens: int
    seconds: float
    context_tokens: int = 0
    """Öneğin **değişken** kısmının jeton sayısı: özet, geçmiş, bağlam bloğu ve güncel tur
    (P27). Sabit önek — yönerge ve katalog — dışarıda; o her senaryoda aynı ve kovayı
    ayırmıyor. Sunucunun sayacından geliyor, tahmin edilmiyor (Kural 10)."""
    ttft: float = 0.0
    """İlk token'a kadar geçen süre (§6, §19.4). `seconds` tamamlanmayı ölçüyor; ikisi
    ayrı, çünkü tamamlanma üretilen token sayısıyla büyür, ilk ses büyümez."""
    failures: Sequence[str] = field(default_factory=tuple)
    """Ne yanlış gitti — raporun "neden" sütunu."""
    answer: str | None = None
    """Tool sonucu geri beslendikten sonra üretilen yanıt. Yanıt turu koşulmadıysa `None`."""
    unsupported_numbers: Sequence[str] = field(default_factory=tuple)
    """Yanıtta geçip ne tool sonucunda ne kullanıcı turunda bulunan sayılar."""
    answer_graded: bool = False
    """Yanıt, desteksiz sayı sayacının **paydasına giriyor** mu (P26).

    `answer` dolu olmak yetmiyor: çağrı üretilmeyen senaryolarda modelin düz metni de
    kaydediliyor ama hazır bir tool sonucu olmadığı için "sonuçta var mıydı" sorusunun
    mekanik cevabı yok. O satırlar rapora kanıt olarak giriyor (Kural 13), hiçbir oranın
    paydasına girmiyor (Kural 14).
    """
    unsupported_quotes: Sequence[str] = field(default_factory=tuple)
    """Yanıtta tırnak içinde geçip ne tool sonucunda ne de kullanıcı/geçmiş turlarında
    bulunan alıntılar (P26). Sayı sayacının eşi, ayrı bir sütun: mevcut sayacın değerini
    değiştirmek `docs/faz2-olcum.md`'den beri süren karşılaştırmayı bozardı."""
    step2_call: ToolCall | None = None
    """İkinci adımda üretilen çağrı. İkinci adım koşulmadıysa anlamsız (`step2_run`)."""
    step2_run: bool = False
    step2_tool_correct: bool | None = None
    step2_arguments_correct: bool | None = None
    prefix: Prefix = Prefix.OLCUM
    """Hangi önekle koşuldu (P27). Satırın kendisinde duruyor, yalnızca koşu etiketinde
    değil: iki önek aynı raporda yan yana ve hangi sayının hangi dünyaya ait olduğu
    etiketten okunmak zorunda kalırsa ilk yanlış okuma orada olur."""
    error: str | None = None
    """Senaryo ölçülemedi — servis iki denemede de düştü (bkz. `run_all`). Dolu olan
    satırlar hiçbir doğruluk paydasına girmiyor: modelin yanlışı değil, ölçümün eksiği."""


def system_prompt(registry: Registry, call_format: CallFormat) -> str:
    """§8.1'in sabit öneki: çağrı nasıl yazılır, sonra hangi tool'lar var.

    **Ölçüm öneğinin başı** — rol metni yok, çünkü `docs/faz2-olcum.md`'den beri böyle
    ölçüldü. Üretimin öneği için `agent.prompt.system_prompt` var (`Prefix.URETIM`).
    """
    return f"{instructions(call_format)}\n\n{catalog_text(registry)}"


def user_prompt(scenario: Scenario) -> str:
    """Bağlam bloğu (değişken, en sonda) + güncel tur."""
    return f"[bağlam] şu an: {NOW}\n\n{scenario.text}"


def called_line(called: Sequence[str]) -> str:
    """2026-08-13 ile 2026-08-16 arasındaki geçmiş biçimi: yalnızca adlar, sonuç yok.

    **Üretimde artık yok** — `turn/runner.py` tool adımını çağrı + sonuç olarak yazıyor
    (`agent/loop.py:ToolDone`). Burada duruyor çünkü tek turluk kümelerin geçmişi bu
    biçimde yazılmış ve `docs/faz2-olcum.md`'den beri okunan sayılar ona göre; biçimi
    değiştirmek elli senaryoyu yeniden ölçmek demek.
    """
    return "[araç] bu turda çağrıldı: " + ", ".join(called)


def history_messages(scenario: Scenario, *, tool_rows: bool = True) -> list[PromptMessage]:
    """Senaryonun geçmişi.

    **Bu artık üretimin biçimi değil ve bilerek öyle** (2026-08-16). Üretim tool adımını
    çağrı (`assistant`) + sonuç (`tool`) olarak yazıyor; buradaki kümelerin senaryolarında
    ise geçmiş turun **sonucu yok**, yalnızca çağrılan tool'un adı var (`scenarios.py`).
    Sonucu uydurmak, ölçümün kendi varsayımını doğrulaması olurdu.

    Sonuç: **tek turluk kümeler 2026-08-16 öncesinin geçmişini ölçmeye devam ediyor.**
    Üretimin yeni biçimini ölçen yer `evals/session.py` — orada tur sonuçları senaryoda
    yazılı, dolayısıyla üretimin dizisi birebir kurulabiliyor. Kabul kapısı da o zaten.
    Bu kümeleri yeni biçime taşımak senaryolara sonuç alanı eklemek demek; elli senaryo
    bilerek elle sürülmüyor (CLAUDE.md, "kümeyi sonuca uydurma").

    `tool_rows=False` 2026-08-13 öncesini kurar (iz satırı hiç yok).
    """
    messages: list[PromptMessage] = []
    for past in scenario.history:
        messages.append(PromptMessage("user", past.user))
        if past.tool is not None and tool_rows:
            messages.append(PromptMessage("tool", called_line([past.tool])))
        messages.append(PromptMessage("assistant", past.assistant))
    return messages


def prefix_messages(
    registry: Registry,
    call_format: CallFormat,
    scenario: Scenario,
    *,
    prefix: Prefix,
    role: str | None,
    tool_rows: bool,
    language_rule: str | None = None,
) -> list[PromptMessage]:
    """Senaryonun öneği — hangi dünyada ölçtüğümüze göre (P27).

    **`ÜRETİM` dalı kendi dizisini kurmuyor**, `agent.prompt.build_messages`'ı çağırıyor.
    Buraya ikinci bir kopya yazmak, üretimin sırası değiştiğinde ölçümün sessizce eski
    sırayı ölçmeye devam etmesi demekti — P27'nin varlık sebebi tam olarak bu ayrışmaydı.
    Bir test iki tarafın aynı fonksiyondan geldiğini kilitliyor.

    **`ÖLÇÜM` dalı bilerek elle kuruyor.** Bugüne kadarki bütün raporlar bu dizi ile
    ölçüldü ve bir baytı değişirse hiçbiri karşılaştırılamaz.
    """
    history = history_messages(scenario, tool_rows=tool_rows)
    match prefix:
        case Prefix.OLCUM:
            return [
                PromptMessage("system", system_prompt(registry, call_format)),
                *history,
                PromptMessage("user", user_prompt(scenario)),
            ]
        case Prefix.URETIM:
            if role is None:
                raise ValueError("üretim öneği rol metni olmadan kurulamaz (§8.1)")
            # Dil kuralının yeri biçime bağlı ve kararı `main.py` veriyor; ölçüm onun
            # dizisini taklit ediyor (P27'nin kuralı). Yerelde katalogu şablon ekliyor
            # ve bizim metnimizin arkasına koyuyor, yani sistem promptunun sonu artık
            # öneğin sonu değil — kural bağlam bloğuna geçiyor.
            native = call_format is CallFormat.YEREL
            return list(
                build_messages(
                    agent_system_prompt(
                        registry,
                        call_format,
                        role=role,
                        language_rule=None if native else language_rule,
                    ),
                    context=ContextBlock(
                        now=NOW,
                        facts=scenario.facts,
                        language_rule=language_rule if native else None,
                    ),
                    user=scenario.text,
                    summary=scenario.summary,
                    history=history,
                )
            )


def grammar_for(registry: Registry, call_format: CallFormat) -> str:
    match call_format:
        case CallFormat.CLI:
            return cli_grammar(registry)
        case CallFormat.JSON:
            return json_grammar(registry)
        case CallFormat.YEREL:
            # Yerel biçimin grameri yok; kolu `evals/session.py --yerel` koşuyor.
            raise ValueError("yerel biçimin grameri yok")


@dataclass(frozen=True, slots=True)
class _Attempt:
    """Bir üretim + düzeltme döngüsünün tamamı. `call is None` iki şey demek olabilir:
    model düz metin yazdı ya da tavana kadar geçerli bir çağrı üretemedi — `failures`
    ikisini ayırıyor."""

    messages: Sequence[PromptMessage]
    output: str
    call: ToolCall | None
    unknown_tool: int
    unknown_argument: int
    corrections: int
    failures: Sequence[str]
    ttft: float
    """İlk token'a kadar geçen süre — **ilk** üretimin, düzeltme turlarının değil.

    §6'nın bütçesi bu: dalın ilk token'da belli olması ilk sesin ne kadar beklediğini
    belirliyor ve §19.4 hâlâ açık. `ort. sn` bunu göstermiyordu; tamamlanma süresi
    üretilen token sayısıyla birlikte büyüyor, ilk ses ise büyümüyor.
    """
    native: NativeCall | None = None
    """Yerel biçimde modelin ürettiği ham çağrı. Yanıt turunda geçmişe `tool_calls`
    olarak yazılması gerekiyor: metne çevrilirse model biçimi kopyalıyor
    (`docs/faz-b-yerel.md`)."""


async def _native_attempt(
    registry: Registry, llm: LLMClient, messages: Sequence[PromptMessage]
) -> _Attempt:
    """Yerel biçimde tek üretim (`CallFormat.YEREL`).

    **Düzeltme döngüsü yok** ve bu bir eksiklik değil, ölçülen şeyin farkı: `_attempt`'in
    düzelttiği hata sınıfı bozuk *sözdizimi* ve yerel biçimde sözdizimini sunucu üretiyor.
    Kalan doğrulama defterin kendisi (`from_native`); geçersizse çağrı düşmüş sayılıyor ve
    `failures`'a yazılıyor.

    **`uydurulan tool` sayacı burada gerçekten modeli ölçüyor.** §17.1'in uyarısı gramere
    aitti: orada ad literal alternatifti, yani uydurulamazdı. Şema öyle bir güvence
    vermiyor.
    """
    started = time.monotonic()
    ttft = 0.0
    text: list[str] = []
    calls: list[NativeCall] = []
    stream = llm.stream_native(messages, tools=schemas(registry), max_tokens=MAX_TOKENS)
    async with aclosing(stream) as events:
        async for event in events:
            if not ttft:
                ttft = time.monotonic() - started
            if isinstance(event, NativeCall):
                calls.append(event)
            else:
                text.append(event)

    # Tur başına bir çağrı ölçülüyor; fazlası sessizce atılmıyor (Kural 13).
    failures = [f"fazladan çağrı: {call.name}" for call in calls[1:]]
    call: ToolCall | None = None
    unknown_tool = 0
    unknown_argument = 0
    if calls:
        try:
            call = from_native(registry, calls[0])
        except UnknownToolError as exc:
            unknown_tool += 1
            failures.append(str(exc))
        except (UnknownArgumentError, ToolArgumentError) as exc:
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
        native=calls[0] if calls else None,
    )


async def _attempt(
    registry: Registry,
    llm: LLMClient,
    call_format: CallFormat,
    messages: Sequence[PromptMessage],
    *,
    max_corrections: int,
) -> _Attempt:
    if call_format is CallFormat.YEREL:
        return await _native_attempt(registry, llm, messages)
    grammar = grammar_for(registry, call_format)
    unknown_tool = 0
    unknown_argument = 0
    corrections = 0
    output = ""
    call: ToolCall | None = None
    failures: list[str] = []
    ttft = 0.0

    while True:
        # İlk parçaya kadar geçen süre ayrıca ölçülüyor: §6'nın bütçesi ilk ses, ve
        # tamamlanma süresi üretilen token sayısıyla büyüdüğü için onu temsil etmiyor.
        # Yalnızca **ilk** üretimden alınıyor — düzeltme turu kullanıcının beklediği
        # ilk sesin öncesinde değil, zaten kaybedilmiş bir turun içinde.
        started = time.monotonic()
        chunks: list[str] = []
        async for chunk in llm.stream(messages, grammar=grammar, max_tokens=MAX_TOKENS):
            if not chunks and corrections == 0:
                ttft = time.monotonic() - started
            chunks.append(chunk)
        output = "".join(chunks)
        if not is_call(output):
            break
        try:
            call = parse(registry, call_format, output)
            registry.get(call.name).validate(call.arguments)
            break
        except UnknownToolError as exc:
            unknown_tool += 1
            feedback = str(exc)
        except UnknownArgumentError as exc:
            unknown_argument += 1
            feedback = str(exc)
        except CallParseError as exc:
            feedback = str(exc)
        except ToolArgumentError as exc:
            feedback = f"{exc}\n{exc.usage}"
        call = None
        failures.append(feedback.splitlines()[0])
        if corrections >= max_corrections:
            break
        corrections += 1
        messages = [
            *messages,
            PromptMessage("assistant", output),
            PromptMessage("user", feedback),
        ]

    return _Attempt(
        messages,
        output,
        call,
        unknown_tool,
        unknown_argument,
        corrections,
        tuple(failures),
        ttft,
    )


async def run_scenario(
    registry: Registry,
    llm: LLMClient,
    call_format: CallFormat,
    scenario: Scenario,
    *,
    max_corrections: int = MAX_CORRECTIONS,
    tool_rows: bool = True,
    prefix: Prefix = Prefix.OLCUM,
    role: str | None = None,
    language_rule: str | None = None,
) -> ScenarioResult:
    """Bir senaryoyu koşar; düzeltme turları dâhil tek bir sonuç üretir."""
    messages: Sequence[PromptMessage] = prefix_messages(
        registry,
        call_format,
        scenario,
        prefix=prefix,
        role=role,
        tool_rows=tool_rows,
        language_rule=language_rule,
    )

    # Kova, öneğin değişken kısmının jeton sayısından çıkıyor (P27). Sistem mesajı
    # dışarıda: her senaryoda aynı ve hiçbir kovayı diğerinden ayırmıyor.
    context_tokens = await llm.count_tokens(
        "\n".join(message.content for message in messages if message.role != "system")
    )

    started = time.monotonic()
    first = await _attempt(
        registry, llm, call_format, messages, max_corrections=max_corrections
    )
    seconds = time.monotonic() - started

    tool_correct, arguments_correct, graded = _grade(scenario, first.call)

    answer: str | None = None
    answer_graded = False
    unsupported: tuple[str, ...] = ()
    quotes: tuple[str, ...] = ()
    step2: _Attempt | None = None
    step2_tool: bool | None = None
    step2_arguments: bool | None = None
    if first.call is None:
        # Çağrı yok: modelin ürettiği düz metnin kendisi zaten kullanıcının duyacağı
        # yanıt. İkinci bir üretim yapılmıyor — geri beslenecek bir sonuç yok ve olmayan
        # bir tool sonucunu uydurup beslemek ölçülen şeyi bozardı. Kaydediliyor ama
        # yargılanmıyor (P26): `answer_graded` `False` kalıyor.
        answer = first.output
        quotes = _unsupported_quotes(first.output, _sources(scenario, fed=None))
    elif scenario.result is not None and tool_correct:
        if scenario.step2 is None:
            answer, unsupported, quotes = await _answer(
                llm, first.messages, first.output, scenario, first.native
            )
            answer_graded = True
        else:
            step2 = await _step2(
                registry,
                llm,
                call_format,
                first,
                scenario,
                max_corrections=max_corrections,
            )
            step2_tool, step2_arguments, step2_graded = _grade_call(
                scenario.step2.expected, step2.call, where="2. adım"
            )
            graded = [*graded, *step2_graded]

    return ScenarioResult(
        scenario_id=scenario.id,
        kind=scenario.kind,
        context=context_of(scenario, context_tokens),
        call_format=call_format,
        model=llm.name,
        output=first.output,
        call=first.call,
        tool_correct=tool_correct,
        arguments_correct=arguments_correct,
        unknown_tool=first.unknown_tool + (step2.unknown_tool if step2 else 0),
        unknown_argument=first.unknown_argument + (step2.unknown_argument if step2 else 0),
        corrections=first.corrections + (step2.corrections if step2 else 0),
        tokens=await llm.count_tokens(first.output),
        seconds=seconds,
        context_tokens=context_tokens,
        ttft=first.ttft,
        failures=tuple([*first.failures, *graded]),
        answer=answer,
        answer_graded=answer_graded,
        unsupported_numbers=unsupported,
        unsupported_quotes=quotes,
        step2_call=step2.call if step2 else None,
        step2_run=step2 is not None,
        step2_tool_correct=step2_tool,
        step2_arguments_correct=step2_arguments,
        prefix=prefix,
    )


async def _step2(
    registry: Registry,
    llm: LLMClient,
    call_format: CallFormat,
    first: _Attempt,
    scenario: Scenario,
    *,
    max_corrections: int,
) -> _Attempt:
    """Tool sonucunu geri besleyip **ikinci adımı** üretir (P25.2).

    Gramer yine tool grameri, `PROSE_GRAMMAR` değil: ölçülen şey ikinci bir çağrının
    gelip gelmediği ve doğru olup olmadığı, ve negatif kontrol satırlarında (`Step2.expected`
    `None`) doğru cevap zaten "çağrı yok" — o dalı gramerle kapatmak, ölçülmek istenen
    hatayı üretilemez kılardı.
    """
    assert scenario.step2 is not None
    fed = json.dumps(scenario.result, ensure_ascii=False, sort_keys=True)
    messages = [
        *first.messages,
        *_fed_messages(first.output, fed, first.native),
    ]
    if scenario.step2.user is not None:
        messages.append(PromptMessage("user", scenario.step2.user))
    return await _attempt(registry, llm, call_format, messages, max_corrections=max_corrections)


def _fed_messages(output: str, fed: str, native: NativeCall | None) -> list[PromptMessage]:
    """Çağrı + sonuç ikilisi, biçime göre.

    **Metin biçimlerinde eski dizi baytı baytına korunuyor** — çağrı `assistant` metni,
    sonuç `[tool sonucu]` etiketli bir `user` mesajı. Üretim bunu `tool` rolüyle yapıyor
    ve ayrışma bilinçli: `docs/faz2-olcum.md`'den beri her rapor bu diziyle ölçüldü ve bir
    baytı değişirse hiçbiri karşılaştırılamaz (P13). Üretimin dizisini ölçen yer
    `evals/session.py`.

    **Yerel biçimde eski dizi zaten yok**, yani korunacak bir karşılaştırma da yok:
    çağrı `tool_calls` alanında, sonuç `tool` rolünde — üretimin dizisinin aynısı.
    """
    if native is None:
        return [
            PromptMessage("assistant", output),
            PromptMessage("user", f"[tool sonucu] {fed}"),
        ]
    return [
        PromptMessage("assistant", output, (native,)),
        PromptMessage("tool", fed),
    ]


_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


_QUOTED = re.compile(r"[\"“]([^\"“”]{2,})[\"”]")
"""Yanıttaki tırnaklı alıntı. Düz ve tipografik çift tırnak; tek tırnak **yok**, çünkü
Türkçe kesme işareti (`Denizli'de`) onunla ayrılamaz. İki karakterden kısası da yok:
tek harflik bir tırnak alıntı değil."""


def _sources(scenario: Scenario, *, fed: str | None) -> str:
    """Bir iddianın dayanabileceği metinlerin tamamı: tool sonucu, kullanıcının turu ve
    geçmişin kendisi. Geçmiş de kaynak: modelin kendi eski cümlesini tekrar etmesi bir
    uydurma değil, ölçülen şey **yeni** içerik icat etmesi."""
    history = " ".join(f"{past.user} {past.assistant}" for past in scenario.history)
    # Özet ve olgular da öneğin içinde (P27): oradan okunan bir sayı ya da alıntı
    # desteklidir. Kaynak listesine girmezlerse üretim öneğiyle koşulan her senaryo
    # kendi bağlamından okuduğu için "uydurmuş" sayılırdı.
    return " ".join(
        part
        for part in (fed, user_prompt(scenario), history, scenario.summary, scenario.facts)
        if part
    )


def _unsupported_quotes(answer: str, sources: str) -> tuple[str, ...]:
    """Yanıtta tırnak içinde geçip kaynakların hiçbirinde bulunmayan alıntılar (P26).

    **Mekanik ve dar, bilerek.** `issues.md` #3'ün uydurması tırnak içinde bir listeydi
    ("Süt, ekmek, yumurta") ve tırnaklı alıntı, bir hakem modeli olmadan "kaynakta var
    mıydı" sorusuna cevap verilebilen ikinci şey — birincisi sayılar. Tırnaksız serbest
    cümle hâlâ kapsam dışı ve rapor bunu yazıyor.

    Karşılaştırma birebir: harf katlaması Türkçe'de `I`/`ı` üzerinde yanlış çalışır.
    """
    return tuple(
        match.group(1)
        for match in _QUOTED.finditer(answer)
        if match.group(1).strip(" .,:;!?") not in sources
    )


async def _answer(
    llm: LLMClient,
    messages: Sequence[PromptMessage],
    call_output: str,
    scenario: Scenario,
    native: NativeCall | None = None,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Tool sonucunu geri besleyip yanıtı üretir ve desteksiz sayıları çıkarır.

    Gramer `PROSE_GRAMMAR`: yanıt turunda ikinci bir çağrı ölçülen şey değil, ve gramer
    onu üretilemez kılıyor — `agent/loop.py`'nin sınırdaki kapanışıyla aynı gerekçe.
    """
    fed = json.dumps(scenario.result, ensure_ascii=False, sort_keys=True)
    answer = "".join(
        [
            chunk
            async for chunk in llm.stream(
                [*messages, *_fed_messages(call_output, fed, native)],
                grammar=PROSE_GRAMMAR,
                max_tokens=MAX_TOKENS,
            )
        ]
    )
    # Kaynaklar: tool sonucu, kullanıcı turu ve **önekteki bloklar** (P27). Geçmiş turlar
    # bilerek dışarıda: bu sayaç `docs/faz2-olcum.md`'den beri bu iki kaynakla ölçülüyor
    # ve üçüncüsünü eklemek geçmişli kümelerin eski sayılarını sessizce oynatırdı. Özet ve
    # olgu alanları yeni, yani onları eklemek hiçbir eski satırı kıpırdatmıyor.
    supported = (
        _numbers(fed)
        | _numbers(user_prompt(scenario))
        | _numbers(scenario.summary or "")
        | _numbers(scenario.facts or "")
    )
    unsupported = tuple(n for n in _numbers(answer) if n not in supported)
    return answer, unsupported, _unsupported_quotes(answer, _sources(scenario, fed=fed))


def _numbers(text: str) -> set[str]:
    """Ondalık ayracı tek biçime indiriliyor: `9,4` ile `9.4` aynı sayı. Sondaki sıfırlar
    da atılıyor, yoksa `31` ile `31.0` iki farklı iddia sayılırdı."""
    return {_normalize(match.group()) for match in _NUMBER.finditer(text)}


def _normalize(number: str) -> str:
    value = number.replace(",", ".")
    return value.rstrip("0").rstrip(".") if "." in value else value


def _grade(scenario: Scenario, call: ToolCall | None) -> tuple[bool, bool | None, list[str]]:
    """Beklenen sonuç, ve varsa kabul edilen diğerleri (P27).

    Alternatif tutarsa **onun** notu dönüyor; hiçbiri tutmazsa birinci beklentinin
    gerekçesi raporlanıyor — rapora "şunu bekliyordum" diye tek bir cümle girmeli, üç
    ayrı beklentinin üç ayrı şikâyeti değil.
    """
    primary = _grade_call(scenario.expected, call)
    if primary[0] or not scenario.accepted:
        return primary
    for alternative in scenario.accepted:
        graded = _grade_call(alternative, call)
        if graded[0]:
            return graded
    return primary


def _grade_call(
    expected: ExpectedCall | None, call: ToolCall | None, *, where: str = ""
) -> tuple[bool, bool | None, list[str]]:
    """Tool seçimi ve argüman doğruluğu. İkincisi yalnızca birincisi doğruysa tanımlıdır —
    yanlış tool'un argümanını doğru saymak ya da yanlış saymak, ikisi de anlamsız.

    `where` yalnızca hata metnine giriyor: ikinci adımın hatası raporda birincininkiyle
    aynı satırda duruyor ve hangisi olduğu yazılmazsa okunamaz.
    """
    prefix = f"{where}: " if where else ""
    if expected is None:
        if call is None:
            return True, None, []
        return False, None, [f"{prefix}düz metin beklenirken {call.name} çağrıldı"]
    if call is None:
        return False, None, [f"{prefix}{expected.tool} beklenirken çağrı üretilmedi"]
    if call.name != expected.tool:
        return False, None, [f"{prefix}{expected.tool} beklenirken {call.name} çağrıldı"]
    problems = [f"{prefix}{problem}" for problem in _argument_problems(expected, call)]
    return True, not problems, problems


_SENTENCE_END = ".!?"


def _comparable(value: str) -> str:
    """Cümle sonu noktalaması iki tarafta da atılır.

    Kullanıcının cümlesini bitiren nokta argümanın içeriği değil: "süt al." ile "süt al"
    aynı nottur ve ölçüm bunu hata sayarsa modelin doğrusunu yanlış raporlar. İlk koşuda
    argüman hatalarının yarısı buydu.

    **Bu bir büyük/küçük harf katlaması değil.** Katlama Türkçe'de `I`/`ı` üzerinde yanlış
    çalışır ve hâlâ yapılmıyor; burada atılan tek şey en sondaki cümle noktalaması.
    """
    return value.rstrip(_SENTENCE_END)


def _argument_problems(expected: ExpectedCall, call: ToolCall) -> list[str]:
    problems = []
    for name, want in expected.arguments.items():
        if name not in call.arguments:
            problems.append(f"{name} eksik")
        elif isinstance(want, str) and _comparable(call.arguments[name]) != _comparable(want):
            problems.append(f"{name}: {want!r} beklenirken {call.arguments[name]!r} geldi")
    for name in call.arguments:
        if name not in expected.arguments:
            problems.append(f"{name} fazladan verildi")
    return problems


async def run_all(
    registry: Registry,
    llm: LLMClient,
    call_format: CallFormat,
    scenarios: Sequence[Scenario],
    *,
    max_corrections: int = MAX_CORRECTIONS,
    tool_rows: bool = True,
    prefix: Prefix = Prefix.OLCUM,
    role: str | None = None,
    language_rule: str | None = None,
) -> list[ScenarioResult]:
    """Bütün kümeyi koşar. **Servis hatası koşuyu bitirmez, senaryoyu bitirir.**

    Sebebi ölçülmüş bir olay: 35B'nin koşusu 28 üretimin 26'ncısında `akış kesildi` ile
    öldü ve rapor sonda yazıldığı için 25 dakikalık ölçümün tamamı kayboldu (`issues.md`
    #2 aynı kesintiyi üretimde de görüyor). Bir kesinti ölçüm aracını çökertmemeli.

    **Senaryo bir kez baştan tekrar denenir.** Bu P12'nin akış yasağını çiğnemiyor:
    orada yasak olan, yarısı tüketilmiş bir üretimi tekrar oynatmak — token'ları iki kez
    yayar. Burada yapılan, senaryoyu sıfırdan koşmak; ortada tüketilmiş bir akış yok.

    **İki denemede de düşen senaryo sessizce atlanmıyor** (Kural 13): `error` alanıyla
    kaydediliyor, doğruluk paydalarının dışında tutuluyor ve rapora kendi bölümüyle
    giriyor. Yanlış cevap sayılsaydı model, servisin kopmasından sorumlu tutulurdu;
    hiç yazılmasaydı payda sessizce küçülür ve rapor eksikliğini gizlerdi.
    """
    results = []
    for scenario in scenarios:
        for attempt in (1, 2):
            try:
                results.append(
                    await run_scenario(
                        registry,
                        llm,
                        call_format,
                        scenario,
                        max_corrections=max_corrections,
                        tool_rows=tool_rows,
                        prefix=prefix,
                        role=role,
                        language_rule=language_rule,
                    )
                )
                break
            except ServiceUnavailableError as error:
                log.warning(
                    "senaryo servis hatasıyla düştü",
                    scenario=scenario.id,
                    attempt=attempt,
                    error=str(error),
                )
                if attempt == 2:
                    results.append(
                        _service_error(scenario, call_format, llm, error, prefix=prefix)
                    )
    return results


def _service_error(
    scenario: Scenario,
    call_format: CallFormat,
    llm: LLMClient,
    error: ServiceUnavailableError,
    *,
    prefix: Prefix = Prefix.OLCUM,
) -> ScenarioResult:
    """Ölçülemeyen senaryo. `tool_correct=False` ama rapor `error` dolu satırları
    paydalardan çıkarıyor — burada `False` yalnızca "doğru değil" demek, "model yanlış
    yaptı" değil."""
    return ScenarioResult(
        scenario_id=scenario.id,
        kind=scenario.kind,
        context=context_of(scenario, 0),
        call_format=call_format,
        model=llm.name,
        output="",
        call=None,
        tool_correct=False,
        arguments_correct=None,
        unknown_tool=0,
        unknown_argument=0,
        corrections=0,
        tokens=0,
        seconds=0.0,
        prefix=prefix,
        error=str(error),
    )

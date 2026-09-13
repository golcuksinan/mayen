"""Süreç giriş noktası: `uv run --env-file .env python -m mayen`.

P15 sunucuyu yazdı ama kuran bir yer yoktu — parçalar yalnızca testlerde elle
birleştiriliyordu. Burası o tek yer: yapılandırma okunur, veritabanı açılır, adaptörler
kurulur, tur koşucusu ile oturum ve soket birbirine bağlanır.

**Katman değil, montaj.** Her şeyi import eden tek modül burası ve kimse burayı import
etmiyor; sınır testinde `transport`'un da üstünde duruyor. Bağlantıları kuran yerin tek
olması, "bu nesneyi kim yaratıyor" sorusunun tek cevabı olması demek.

**Sayılar burada, sınıflarda değil.** `max_steps`, `min_chars`, `max_wait_seconds`,
`approval_timeout_seconds` bilerek varsayılansız yazılmıştı: §19'da bu sayılar yok ve bir
sınıfın içine gömülen sayı, ölçülmüş bir karar gibi görünür. Süreç ise bir sayı vermek
zorunda. Aşağıdakiler o yüzden **işletim değerleri**: §19.4 ölçülünce değişecekleri
baştan yazılı ve hepsi tek ekranda duruyor.

**LLM ve TTS gerçek, STT/konuşmacı sahte.** §19.2'nin LLM yarısı 2026-08-15'te, TTS yarısı
Faz 7'de kapandı (Kokoro, `services/kokoro/`); sahibi STT'yi bir süre daha sahte tutmayı
seçti. Sahte STT metin segmentini transkript sayıyor, yani sistem bugün metinle giriyor ve
sesle çıkıyor. Gerçek uçlar geldiğinde değişecek yer bu dosyadaki iki satır — üst
katmanların hiçbiri.

**Hangisinin gerçek olduğu yapılandırmadan** (`MAYEN_STT`, `MAYEN_TTS`; `baslat`'ın
`--stt`/`--tts` bayrakları bunları veriyor). Sahte TTS bir test kolaylığı değil yalnızca:
Kokoro servisini ayağa kaldırmadan uçtan uca konuşmak isteyen kişi de onu seçiyor.
`MAYEN_STT=real` ise bilerek **hata**: seçilecek bir STT modeli yok (§19.2) ve sessizce
sahteye düşmek açık bir maddeyi varsayımla kapatmak olurdu.

**Bellek burada kuruluyor ve boştaki işi burası başlatıyor.** Pencere (§11.1) tur
koşucusuna, `Digest` (§11.2/§11.3) ise `BackgroundWork`'e veriliyor; oturum onu yalnızca
`IdleWork` olarak görüyor. Bağlam boyutu yapılandırmada **yok**: sunucuya soruluyor
(§11.1), yani modeli değiştirmek burada bir sayı düzeltmeyi gerektirmiyor.

**Kimlik henüz kimseyi tanımıyor.** §19.3'ün eşikleri açık; gömü çıkarılıyor (§6, koşucu
zaten yapıyor) ama karşılaştırılmıyor. Eşiksiz bir eşleştirme uydurmak yerine kimlik
`TANINMAYAN` dönüyor: yetki matrisinin (§10.2) o satırında yalnızca sohbet var, yani
sistem bu hâliyle hiçbir tool'u çalıştırmaz. Bu bir eksiklik ve açılışta uyarıya
yazılıyor (Kural 13); sessizce `SAHİP` dönmek Kural 6'yı ihlal ederdi.

**Bunun geçici kapısı `MAYEN_ASSUME_OWNER`** (2026-08-10 kararı). Verildiğinde gömüye
bakılmadan her segment `SAHİP` sayılır, böylece §19.3 beklenmeden tool akışı gerçek
modelle çalıştırılabilir. Kural 6 bozulmuyor: yasakladığı şey sahipliğin **sesle**
verilmesi, buradaki kapı ise kabuk — bayrağı verebilen kişi makinenin başında (§19.14'ün
kurulum betiği de aynı gerekçeyle bir kabuk kapısı). Açık olduğu her açılışta uyarı
yazılıyor; konuşmacı tanıma gerçek olduğunda bayrak silinir.
"""

import argparse
import asyncio
import contextlib
import signal
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from mayen.adapters.desktop import SystemDesktop
from mayen.adapters.fakes.speaker import FakeSpeaker
from mayen.adapters.fakes.stt import FakeSTT
from mayen.adapters.fakes.tts import FakeTTS
from mayen.adapters.kokoro import KokoroTTS
from mayen.adapters.llamacpp import LlamaCppLLM
from mayen.adapters.llm import LLMClient
from mayen.adapters.speaker import Embedding
from mayen.adapters.stt import STTClient
from mayen.adapters.tts import TTSClient
from mayen.agent.calls import CallFormat
from mayen.agent.loop import AgentLoop
from mayen.agent.prompt import load_role, system_prompt
from mayen.config import Config, ConfigError, ServiceKind, load
from mayen.data import backup
from mayen.data.db import Database, DatabaseError
from mayen.data.migrate import migrate
from mayen.data.repositories.conversation import MessageRepository, SummaryRepository
from mayen.data.repositories.courses import CourseRepository
from mayen.data.repositories.facts import FactRepository
from mayen.data.repositories.notes import NoteRepository
from mayen.data.repositories.people import PeopleRepository
from mayen.data.repositories.tasks import TaskKind, TaskRepository
from mayen.data.repositories.traces import TraceRepository
from mayen.data.schedule import install as install_schedule
from mayen.memory.background import BackgroundWork
from mayen.memory.digest import Digest
from mayen.memory.recall import Recall
from mayen.memory.window import ContextWindow
from mayen.obs.log import configure, get_logger
from mayen.policy.approval import ApprovalResolver
from mayen.policy.authority import Authority, Identity
from mayen.scheduler.announce import Announcer
from mayen.scheduler.loop import Recurring, Scheduler
from mayen.scheduler.phrasing import ReminderVoice
from mayen.scheduler.reminders import reminder_handler
from mayen.session.actor import Session
from mayen.tools.catalog import builtin_registry
from mayen.tools.registry import Registry
from mayen.tools.spec import ToolContext
from mayen.transport.server import Connections, FrameSink, Server
from mayen.turn.runner import Runner

log = get_logger(__name__)

EXIT_CONFIG = 78
"""Kalıcı hata çıkış kodu (`sysexits.h`'nin `EX_CONFIG`'i). Birim dosyası bu kodda yeniden
başlatmıyor; sayı orada ve burada aynı olduğu için kendi adı var."""

CALL_FORMAT = CallFormat.YEREL
"""§19.1: **yerel biçim**, sahibin kararı (2026-08-16). Öncesi ve gerekçesi:

CLI-tarzı metin biçimi P7'den beri çalışan seçimdi ve iki metin biçimi arasındaki fark
hiçbir zaman ayrışmadı (`docs/faz6-olcum.md`, aralıklar çakışıyor). Değişimi getiren şey
bir puan değil, bir **arıza sınıfı**: metin biçimlerinde dal ilk token'da seçiliyor
(§6/C3), yani model bir üretimde ya konuşabiliyor ya çağırabiliyor. İkisini birden
istediğinde çağrıyı düz metnin içinde taklit ediyor, hiçbir şey koşmuyor ve taklit sesli
okunuyor. `<` gramerde yasaklandığında model aynı şeyi köşeli parantezle yazdı —
**karakter yasaklamak bu sınıfı çözmüyor, kılığını değiştiriyor.** Yerel biçimde çakışma
yok: `content` ile `tool_calls` aynı yanıtta durur.

Ölçüm `docs/faz-b-yerel.md`: kabul kapısında 12/15 → 14/15, Wilson aralıkları **örtüşüyor**
(yani bir sıralama değil, Kural 14), ama çevrilen iki tur Faz B'den beri açıkta duran tek
arıza sınıfı. Gereksiz çağrı sayısı değişmedi.

Üç biçim de kodda duruyor ve seçen satır hâlâ burası. Metin biçimleri silinmedi: model
değişirse yeniden ölçülecek şey bu satır, başka hiçbir yer biçime bakmıyor (§8.3)."""

MAX_STEPS = 15
"""§8.2 "sonlu ve küçük" diyor, sayı vermiyor. Dört: kataloğun hiçbir senaryosu üç
çağrıdan fazlasını gerektirmiyor, tavan yine de bir çağrı pay bırakıyor."""

MAX_CORRECTIONS = 2
"""§8.3'ün düzeltme turu tavanı; `evals/runner.py` ölçümde aynı sayıyı kullanıyor."""

MIN_CHARS = 24
"""Cümle bölücünün en kısa parçası. Kısa tutmak ilk sesi öne çeker (§6), fazla kısaltmak
TTS'e cümle değil kırıntı verir. §19.4 ölçülünce ayarlanacak."""

MAX_WAIT_SECONDS = 1.0
"""Noktalama gelmediğinde elde ne varsa seslendirilene kadar beklenen süre."""

APPROVAL_TIMEOUT_SECONDS = 20.0
"""Kural 5 zaman aşımının **sonucunu** sabitliyor (red), süresini değil. Yirmi saniye
soruyu duyup cevap vermeye yeter; sessizlik reddir."""

LLM_TIMEOUT_SECONDS = 120.0
"""Tek bir HTTP isteğinin tavanı, turun gecikme hedefi değil (§19.4 hâlâ açık). Uzun:
ilk istek modelin ısınmasını da bekliyor."""

TTS_TIMEOUT_SECONDS = 60.0
"""Tek bir seslendirme isteğinin tavanı. Cümle başına iş küçük; bu sayı asıl olarak
servisin ilk isteğinde modelin ısınmasını bekliyor. Bağlantı kurulamıyorsa `httpx` zaten
çok daha erken hata veriyor."""

TOOL_TIMEOUT_SECONDS = 10.0
"""`DIŞ` etkili tool'ların dış istemcisi. Tool'un kendi `timeout_seconds`'ı daha kısa;
bu yalnızca ağın en son sınırı."""

RESERVED_OUTPUT_TOKENS = 1024
"""Bağlamın modelin **cevabına** ayrılan payı (§11.1). Bütçenin kendisi sunucudan
soruluyor; bölünmesi bir işletim değeri. Bin yirmi dört: sesli okunacak bir yanıt bu
uzunluğa yaklaşmıyor, tool çağrısı ise çok daha kısa."""

MAX_HISTORY_MESSAGES = 60
"""Pencereye aday olan en fazla mesaj sayısı. Bütçe zaten üstünde bir tavan; bu, token
sayacına gereksiz yere sorulmasını engelleyen alt tavan."""

DIGEST_ON = False
"""Özet (§11.2) ve olgular (§11.3) öneğe girsin mi. **2026-08-16'da kapatıldı.**

Kapatma kararı ölçüme dayanıyor ve gerekçesi üç parça:

- **Bugün faydası ölçülemiyor.** Katman bağlam bütçesi baskı yapsın diye var; pencere
  16384, 60 mesajlık önek ~2961 jeton, yani **%19**, ve `ContextWindow`'un kırpıcısı
  bugüne kadar **hiç çalışmadı** (`docs/faz-b-bicim.md`, iki raporda da `kırpılan: 0`).
- **Bozukluğu ise ölçüldü:** özet birikimli ve anlatı kipinde, getirilen olguların
  yedide altısı yanlış (`docs/faz-a-bulgular.md` §2.1–2.2).
- **Ve arızanın sebebi değildi:** `Digest` tamamen kapalıyken tool çağırmama çöküşü
  birebir aynı turda oluyor (aynı belge §4). Yani taşınan şey ölçülmüş bir zarar ile
  ölçülmemiş bir fayda.

**Silinmedi, kapatıldı.** Konuşmanın oturum sınırı yok; bütçe bir gün dolacak ve o gün
bu katman geri gerekecek. `Digest` yazmaya devam ediyor, kapanan tek şey okuma yolu —
geri açmak bu sabiti `True` yapmak."""

MAX_FACTS = 20
"""Bağlam bloğuna giren olgu sayısı (§11.3). Getirilen olgu sayısının bir sınırı olmalı:
depo büyüdükçe büyüyen bir blok, bütçeyi konuşmanın aleyhine yer."""

DIGEST_KEEP_RECENT = 20
"""Özetin dışında bırakılan en yeni mesajlar. Pencerede kelimesi kelimesine duran bir
mesajı özetlemek, aynı konuşmayı modele iki kez vermek olurdu."""

DIGEST_BATCH = 40
"""Bir boşlukta işlenen en fazla mesaj. Yığın büyüdükçe iş uzar ve preempt edilme
olasılığı artar; küçük yığın birkaç boşlukta biter."""

DIGEST_MAX_TOKENS = 512
"""Özetin ve olgu listesinin üretim tavanı."""

IDLE_DELAY_SECONDS = 5.0
"""Tur bittikten sonra arka plan işinin beklediği süre. Kullanıcı çoğu zaman cevabın
ardından ikinci kez konuşur; sesin bitişiyle üretime başlamak o turun ilk token'ını
bekletirdi (Kural 11)."""

SCHEDULER_TICK_SECONDS = 15.0
"""Zamanlayıcının yoklama aralığı, yani bir hatırlatıcının en fazla ne kadar geç çalacağı.
§12 sayı vermiyor: on beş saniyelik bir sapma konuşma dilinde fark edilmez, daha sık
yoklamak ise boşta duran süreci sebepsiz uyandırır. Toleransla karıştırılmamalı — o
**açılışta** uygulanan ayrı bir sayı ve yapılandırmadan geliyor (§19.13)."""


@dataclass(slots=True)
class App:
    """Kurulmuş sistem. Kapatma sırası kurulumun tersi."""

    config: Config
    database: Database
    http: httpx.AsyncClient
    session: Session
    # Hangi TTS'in kurulduğu dışarıdan görünüyor: seçim yapılandırmadan geliyor ve
    # "sesli mi koşuyorum" sorusunun cevabı kurulan nesnede yazılı.
    tts: TTSClient
    connections: Connections
    server: Server
    scheduler: Scheduler
    announcer: Announcer
    background: BackgroundWork
    course_term: str


@contextlib.asynccontextmanager
async def build(
    config: Config, *, llm: LLMClient | None = None, tts: TTSClient | None = None
) -> AsyncIterator[App]:
    """Her şeyi kurar ve çıkışta söker.

    `llm` ve `tts` dışarıdan verilebiliyor: uçtan uca akışın GPU'suz koşabilmesi §4'ün
    şartı ve testin bu montajı atlaması, tam da montajın doğruluğunu ölçülmemiş bırakırdı.
    Verilmezse ikisi de gerçek servise bağlanır — yani varsayılan üretimdir, test kendi
    sahtesini söylemek zorundadır.
    """
    database = Database(config.db_path)
    http = httpx.AsyncClient(timeout=TOOL_TIMEOUT_SECONDS)
    llm_http = httpx.AsyncClient(base_url=config.llm_url, timeout=LLM_TIMEOUT_SECONDS)
    tts_http = httpx.AsyncClient(base_url=config.tts_url, timeout=TTS_TIMEOUT_SECONDS)
    session: Session | None = None
    scheduler: Scheduler | None = None
    announcer: Announcer | None = None
    background: BackgroundWork | None = None
    try:
        migrate(database)
        courses = CourseRepository(database)
        course_term = _load_schedule(config, courses)

        registry = builtin_registry(config)
        people = PeopleRepository(database)
        facts = FactRepository(database)
        messages = MessageRepository(database)
        summaries = SummaryRepository(database)
        tools = ToolContext(
            config=config,
            http=http,
            desktop=SystemDesktop(),
            people=people,
            notes=NoteRepository(database),
            facts=facts,
            courses=courses,
            tasks=TaskRepository(database),
            course_term=course_term,
        )
        # Rol/dil dosyaları LLM'e bağlanmadan önce okunuyor: ikisi de kalıcı bir
        # yapılandırma hatası, sunucuya ulaşamamak ise geçici. Sıra ters olduğunda
        # eksik rol dosyası `EXIT_CONFIG` yerine geçici hata olarak dışarı çıkar ve
        # birim dosyası onu sonsuz yeniden başlatmaya sokar.
        system, language_rule = _system(registry, config)
        client = llm if llm is not None else await _real_llm(llm_http)

        connections = Connections()
        sink = FrameSink(connections)
        speech = tts if tts is not None else _tts(config, tts_http)
        window = ContextWindow(
            llm=client,
            messages=messages,
            summaries=summaries,
            recall=Recall(facts, people, max_facts=MAX_FACTS),
            reserved_output=RESERVED_OUTPUT_TOKENS,
            max_messages=MAX_HISTORY_MESSAGES,
            digest_on=DIGEST_ON,
        )
        runner = Runner(
            agent=AgentLoop(
                llm=client,
                registry=registry,
                tools=tools,
                call_format=CALL_FORMAT,
                max_steps=MAX_STEPS,
                max_corrections=MAX_CORRECTIONS,
            ),
            system=system,
            language_rule=language_rule,
            stt=_stt(config),
            speaker=FakeSpeaker(),
            tts=speech,
            sink=sink,
            traces=TraceRepository(database),
            identify=_assumed_owner if config.assume_owner else _unidentified,
            resolver=ApprovalResolver(client),
            memory=window,
            min_chars=MIN_CHARS,
            max_wait_seconds=MAX_WAIT_SECONDS,
            approval_timeout_seconds=APPROVAL_TIMEOUT_SECONDS,
        )
        digest = Digest(
            llm=client,
            messages=messages,
            summaries=summaries,
            facts=facts,
            keep_recent=DIGEST_KEEP_RECENT,
            batch_size=DIGEST_BATCH,
            max_tokens=DIGEST_MAX_TOKENS,
        )
        background = BackgroundWork([digest.run], delay_seconds=IDLE_DELAY_SECONDS)
        session = Session(runner, sink, idle=background)
        sink.attach(session)
        await background.start()

        announcer = Announcer(speech, session, sink)
        scheduler = Scheduler(
            TaskRepository(database),
            {
                TaskKind.REMINDER.value: reminder_handler(
                    announcer,
                    # Bildirim cümlesini model yazıyor; not veri olarak gidiyor. Dil
                    # kuralı burada **sistem promptunun sonunda** duruyor ve orada
                    # tutuyor: bu istekte `tools` yok, yani Faz 7'nin ölçtüğü konum
                    # bozulmuyor (turun öneğinde bozuluyor, bkz. `_system`).
                    ReminderVoice(client, _spoken_system(system, language_rule)),
                )
            },
            tick_seconds=SCHEDULER_TICK_SECONDS,
            tolerance_seconds=config.missed_task_tolerance_minutes * 60,
            recurring=[_backup_job(config, database)],
        )
        await scheduler.start()

        if config.assume_owner:
            log.warning(
                "MAYEN_ASSUME_OWNER açık: konuşmacı tanınmıyor, her segment SAHİP sayılıyor",
                open_item="§19.3",
            )
        else:
            log.warning(
                "konuşmacı tanıma kapalı: §19.3 eşikleri açık, herkes TANINMAYAN sayılıyor"
            )
        yield App(
            config=config,
            database=database,
            http=http,
            session=session,
            tts=speech,
            connections=connections,
            server=Server(session, connections, on_connected=announcer.connected),
            scheduler=scheduler,
            announcer=announcer,
            background=background,
            course_term=course_term,
        )
    finally:
        if background is not None:
            await background.stop()
        if scheduler is not None:
            await scheduler.stop()
        if announcer is not None:
            await announcer.close()
        if session is not None:
            await session.close()
        await http.aclose()
        await llm_http.aclose()
        await tts_http.aclose()
        database.close()


async def serve(config: Config, *, ready: asyncio.Event | None = None) -> int:
    """Soketi açar ve bir kapatma işareti gelene kadar dinler."""
    async with build(config) as app:
        socket = await app.server.serve(config.host, config.port)
        log.info("dinleniyor", host=config.host, port=config.port)
        if ready is not None:
            ready.set()
        try:
            await _until_stopped()
        finally:
            socket.close()
            await socket.wait_closed()
    log.info("kapandı")
    return 0


async def _until_stopped() -> None:
    """SIGINT/SIGTERM'i bekler.

    Sinyal kancası `KeyboardInterrupt`'a yeğleniyor: turun ortasında yükselen bir istisna
    kapanışı rastgele bir noktada keserdi; olay beklemek kapanışı tek yere toplar.
    """
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    installed = []
    for name in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # pragma: no cover - Windows
            loop.add_signal_handler(name, stop.set)
            installed.append(name)
    try:
        await stop.wait()
    finally:
        for name in installed:
            loop.remove_signal_handler(name)


def _stt(config: Config) -> STTClient:
    """§19.2'nin STT yarısı açık: `real` diye bir seçenek **yok**.

    Düğme yine de var, çünkü olmaması "STT zaten gerçek" izlenimi bırakırdı; `real`
    verildiğinde süreç açılışta duruyor ve açık maddeyi adıyla söylüyor. Sessizce sahteye
    düşmek, açık bir maddeyi varsayımla kapatmak olurdu (§19'un meta kuralı).
    """
    if config.stt is ServiceKind.REAL:
        raise ConfigError(
            "MAYEN_STT=real: §19.2'nin STT yarısı açık, seçilmiş bir STT modeli yok"
        )
    log.warning("STT sahte: ses girişi çalışmıyor, metin segmenti transkript sayılıyor")
    return FakeSTT()


def _tts(config: Config, http: httpx.AsyncClient) -> TTSClient:
    """Kokoro ya da sahte. Sahte, TTS servisini ayağa kaldırmadan konuşabilmek için —
    yükü okunabilir metin olduğundan istemci cevabı yine gösteriyor."""
    if config.tts is ServiceKind.FAKE:
        log.warning("TTS sahte: ses üretilmiyor, yük metin olarak akıyor", env="MAYEN_TTS")
        return FakeTTS()
    return KokoroTTS(http)


async def _real_llm(http: httpx.AsyncClient) -> LlamaCppLLM:
    """Gerçek LLM istemcisi, **sunucunun kendi örnekleme ayarlarıyla** (2026-08-16).

    Sahibin kararı: modelin önerilen parametreleri var, `llama-server` onlarla açılıyor ve
    onları açgözlü değerlerle ezmek modeli tasarlandığı ayarların dışında koşturmak olurdu.
    Ayarlar yine de **isteğe yazılıyor** — Faz A'nın bulgusu duruyor: bayrakta kalan sayı
    görünmez ve iki raporun farklı bayrak setleriyle koştuğu fark edilmez.

    Sorulamıyorsa **hata yükseliyor**, açgözlüye düşülmüyor (Kural 13): sessizce başka bir
    ayarla koşan bir üretim, bu fonksiyonun engellemek için var olduğu şeyin ta kendisi.
    """
    client = LlamaCppLLM(http)
    sampling = await client.server_sampling()
    log.info("örnekleme sunucudan alındı", **sampling.body())
    return LlamaCppLLM(http, sampling=sampling)


def _system(registry: Registry, config: Config) -> tuple[str, str | None]:
    """Sistem promptu ve **bağlam bloğuna** taşınan dil kuralı (varsa).

    Dosya **zorunlu**: kodda bir yedek metin yok, çünkü iki kopya er geç ayrışır ve
    dosyayı düzenleyen kişi hiçbir şeyin değişmediğini görürdü. Yol verilmemişse süreç
    açılışta durur, sessizce başka bir kişilikle koşmaz (Kural 13).

    **Dil kuralının yerini biçim belirliyor ve o kararı veren yer burası** — §8.3'ün
    "başka hiçbir yer biçime bakmaz" kuralı duruyor, çünkü `main` bir katman değil,
    montaj. Metin biçimlerinde kural sistem promptunun sonunda (katalogdan sonra,
    Faz 7'nin ölçtüğü yer). Yerel biçimde katalogu şablon ekliyor ve **bizim metnimizin
    arkasına** koyuyor, yani o yer artık son değil; kural bağlam bloğunun sonuna geçiyor
    (gerekçe `ContextBlock.language_rule`'da).
    """
    if config.role_path is None:
        raise ConfigError("Rol dosyası verilmedi: MAYEN_ROLE_PATH (örnek: config/rol.txt)")
    role = load_role(config.role_path)
    log.info("rol dosyadan yüklendi", path=str(config.role_path), chars=len(role))
    rule = None
    if config.language_rule_path is not None:
        rule = load_role(config.language_rule_path)
        log.info("dil kuralı yüklendi", path=str(config.language_rule_path))
    if CALL_FORMAT is CallFormat.YEREL:
        return system_prompt(registry, CALL_FORMAT, role=role), rule
    return system_prompt(registry, CALL_FORMAT, role=role, language_rule=rule), None


def _spoken_system(system: str, language_rule: str | None) -> str:
    """Bildirim üretiminin sistem promptu: turun öneği + dil kuralı, en sonda.

    Yerel çağrı biçiminde kural turun öneğinde bağlam bloğuna taşınmıştı, çünkü şablon
    `tools` bloğunu sistem mesajının arkasına koyuyor. Burada `tools` gönderilmiyor —
    bildirim bir tool çağrısı değil — yani sistem promptunun sonu gerçekten öneğin sonu
    ve Faz 7'nin ölçtüğü konum geçerli.
    """
    return system if language_rule is None else f"{system}\n\n{language_rule}"


def _load_schedule(config: Config, courses: CourseRepository) -> str:
    """§19.8: dosya varsa dönem ondan gelir. Yoksa program boş ve bu söylenir."""
    if config.courses_path is None:
        log.warning("ders programı dosyası verilmedi, program boş", env="MAYEN_COURSES_PATH")
        return ""
    term = install_schedule(courses, config.courses_path)
    log.info("ders programı yüklendi", term=term, path=str(config.courses_path))
    return term


def _backup_job(config: Config, database: Database) -> Recurring:
    """§16'nın yedeklemesi: `data/backup.py` P2'den beri hazırdı ama onu tetikleyen bir
    yer yoktu — "yedek alınıyor" sanılan bir kurulum, hiç yedeği olmayan kurulumdur.

    Kural 1 korunuyor: yedek dosyanın sahibi olan süreçte, ayrı bir bağlantıyla alınıyor.
    Ayrı iş parçacığı yok; SQLite'ın kendi yedekleme API'si sayfa sayfa ilerliyor ve
    aralık saatlerle ölçülüyor.
    """

    async def run() -> None:
        backup.run(database, config.backup_dir, config.backup_keep)

    return Recurring(
        name="backup",
        interval_seconds=config.backup_interval_minutes * 60,
        run=run,
    )


async def _unidentified(embedding: Embedding | None) -> Identity:
    """Eşik yok, eşleştirme de yok (bkz. modül başlığı)."""
    return Identity(authority=Authority.TANINMAYAN)


async def _assumed_owner(embedding: Embedding | None) -> Identity:
    """`MAYEN_ASSUME_OWNER`: gömüye bakılmaz, herkes SAHİP sayılır (bkz. modül başlığı).

    Kural 6'nın yasakladığı şey sahipliğin **sesle** verilmesi; buradaki kapı kabuk.
    `person_id` yok: kimliğin bir satırı yok, olmayan bir satırın kimliğini uydurmak
    kaydı ve izi yalan söyler hâle getirirdi.
    """
    return Identity(authority=Authority.SAHIP)


def main(argv: list[str] | None = None) -> int:
    """Süreç sınırı: iz kayda geçiyor, kabuğa çıkış kodu dönüyor (Kural 13).

    **İki hata sınıfı, iki çıkış kodu.** Servis olarak koşarken bu ayrım işletimin
    kendisidir: `EXIT_CONFIG` (78) kalıcı bir hatadır — rol dosyası yok, WOL yapılandırması
    bozuk, veritabanı başka bir süreçte açık. Yeniden başlatmak onu düzeltmez, yalnızca
    hatayı bir yeniden başlatma döngüsünün içine gömer ve kimse görmez; birim dosyası bu
    kodda **başlatmıyor**. Geri kalan her şey 1 ile çıkar ve yeniden başlatılır: LLM
    sunucusu kapalı, port meşgul, disk anlık dolu — hepsi kendiliğinden geçebilir.

    **Ayrımın bilinen boşluğu:** yanlış yazılmış bir veritabanı yolu `sqlite3.OperationalError`
    atıyor, yani kalıcı sayılmıyor ve yeniden başlatılıyor. İstisna türü kalıcı yolu geçici
    disk hatasından ayırmıyor, ayırmayı uydurmak da yanlış olurdu. Sonsuz döngü değil:
    systemd'nin kendi `StartLimitBurst`'ü birimi kısa sürede `failed`'a düşürüyor.
    """
    parser = argparse.ArgumentParser(prog="mayen", description="Mayen sesli asistanı")
    parser.parse_args(argv)

    try:
        config = load()
    except ConfigError as error:
        # Günlükleme henüz kurulmadı: yapılandırma onun da girdisi. Kabuk tek kanal.
        print(f"mayen yapılandırması okunamadı: {error}", file=sys.stderr)
        return EXIT_CONFIG
    configure(level=config.log_level, json=config.log_json)
    try:
        return asyncio.run(serve(config))
    except (ConfigError, DatabaseError) as error:
        log.exception("başlatılamadı", error=str(error), permanent=True)
        print(f"mayen başlatılamadı: {error}", file=sys.stderr)
        return EXIT_CONFIG
    except Exception as error:
        log.exception("başlatılamadı", error=str(error), permanent=False)
        print(f"mayen başlatılamadı: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

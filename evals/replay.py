"""Bir turu veritabanından **birebir** yeniden oynatır (Faz A/A1).

`uv run --env-file .env python -m evals.replay --mesaj 118`

`docs/bellek-kirlenmesi.md`'nin teşhisi bir çıkarımdı: 2026-08-16'nın kaydına bakılıp
"model tool çağırmadı çünkü cevabı zaten önündeydi" denmişti. Bu araç onu ölçüye çeviriyor —
o turda modele giden mesaj dizisi yeniden kurulup tekrar gönderiliyor, sonra **bloklar
tek tek çıkarılarak** hangisinin payı ne olduğu okunuyor. Payların ölçüsü budur.

**Önek üretimin kendi kodundan geliyor, burada ikinci bir kopyası yok.** `ContextWindow`,
`Recall` ve `build_messages` doğrudan çağrılıyor; geçmiş bir pencereyi elle kurmak, ölçümün
üretimin kurmadığı bir öneği ölçmesi demek olurdu — P27'nin hatasının aynısı. Geçmişe
gitmenin yolu bu yüzden bir "geçmiş pencere kurucusu" değil, kopyanın geri sarılması
(`mayen.data.rewind`).

**`mayen.main` import ediliyor** ve bu bilinçli bir istisna. `main` montaj katmanı, kimse
onu import etmez — ama üretimin işletim değerleri (`MAX_HISTORY_MESSAGES`, `MAX_FACTS`,
`RESERVED_OUTPUT_TOKENS`, `CALL_FORMAT`) orada duruyor ve bu aracın tek işi **üretimin
öneğini** kurmak. Buraya kopyalansalardı ilk değişiklikte sessizce ayrışırlardı; ayrışma
tam da bu dosyanın ölçmeye çalıştığı hata sınıfı.

**Kural 1 korunuyor.** Veritabanı önce sahiplenilip (`Database` `flock` alır — `mayen`
koşuyorsa burada gürültüyle durur) `backup_to()` ile kopyalanıyor; geri sarma ve bütün
yazmalar kopyada. Üretim veritabanı okunuyor, değiştirilmiyor.

**Örnekleme varsayılanı geçmişin değeri, bugünün değeri değil.** 2026-08-16'daki tur
sunucunun `presence_penalty=1.5` bayrağıyla koştu; A4 o ayarı isteğe taşıyıp sıfırladı.
Yani "o günkü turu yeniden oynat" demek `--ceza 1.5` demek — varsayılan bu. `--ceza 0`
A4'ün değişikliğinin **ölçüsü**, varsayımı değil.
"""

import argparse
import asyncio
import re
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import httpx

from evals.runner import _Attempt, _attempt
from mayen.adapters.llamacpp import LlamaCppLLM, Sampling
from mayen.adapters.llm import PromptMessage
from mayen.agent.calls import CallFormat
from mayen.agent.prompt import ContextBlock, build_messages, load_role, system_prompt
from mayen.config import Config, ConfigError, load
from mayen.data.db import Database, DatabaseError
from mayen.data.repositories.conversation import MessageRepository, SummaryRepository
from mayen.data.repositories.facts import FactRepository
from mayen.data.repositories.people import PeopleRepository
from mayen.data.rewind import Rewound, rewind
from mayen.main import (
    CALL_FORMAT,
    MAX_CORRECTIONS,
    MAX_FACTS,
    MAX_HISTORY_MESSAGES,
    RESERVED_OUTPUT_TOKENS,
)
from mayen.memory.recall import Recall
from mayen.memory.window import ContextWindow, Window
from mayen.policy.authority import Authority, Identity
from mayen.tools.catalog import builtin_registry
from mayen.tools.registry import Registry

TIMEOUT_SECONDS = 300.0
"""`evals/__main__.py` ile aynı gerekçe: tek yavaş çağrı koşuyu bozmasın."""

HISTORICAL_PRESENCE_PENALTY = 1.5
"""2026-08-16'da yürürlükte olan değer — sunucunun açılış bayrağından geliyordu ve hiç
seçilmemişti (bkz. modül başlığı, `adapters/llamacpp.py:Sampling`)."""


def _drop_answers(history: Sequence[PromptMessage]) -> tuple[PromptMessage, ...]:
    """Asistanın kendi satırlarını geçmişten çıkarır; kullanıcı ve `[araç]` satırları kalır."""
    return tuple(m for m in history if m.role != "assistant")


def _mark_answers(history: Sequence[PromptMessage]) -> tuple[PromptMessage, ...]:
    """Asistan satırlarını `[söylenen]` ile etiketler: bu söylendi, bu bilindi değil."""
    return tuple(
        replace(m, content=f"[söylenen]\n{m.content}") if m.role == "assistant" else m
        for m in history
    )


def _last_answer_only(history: Sequence[PromptMessage]) -> tuple[PromptMessage, ...]:
    """Yalnızca **en son** asistan satırı kalır; daha eskileri çıkar.

    `cevapsız`ın bedeli konuşmanın kendisi: "az önce ne demiştin" diye sorulabilen bir
    asistanın geçmişte hiç cevabı olmaz. Bu ara biçim onu geri veriyor — arızayı üreten
    şey tek bir cevap değil, cevapların **birikmesi** ise yeter; değilse ölçüm söyler.
    """
    kept: list[PromptMessage] = []
    seen = False
    for message in reversed(history):
        if message.role == "assistant":
            if seen:
                continue
            seen = True
        kept.append(message)
    kept.reverse()
    return tuple(kept)


def _rewrite_older_answers(
    history: Sequence[PromptMessage], rewrite: Callable[[str], str]
) -> tuple[PromptMessage, ...]:
    """`rewrite`'ı **en son hariç** bütün asistan satırlarına uygular.

    Son cevap üç biçimde de tam kalıyor: ölçülen şey eskilerin biçimi, ve son cevabı da
    değiştirmek iki değişikliği tek satırda okumak olurdu.
    """
    out: list[PromptMessage] = []
    seen = False
    for message in reversed(history):
        if message.role == "assistant":
            if seen:
                message = replace(message, content=rewrite(message.content))
            seen = True
        out.append(message)
    out.reverse()
    return tuple(out)


def _first_sentence(text: str) -> str:
    """İlk cümle. **Kaba olması bilinçli:** ölçülen şey kısaltmanın işe yarayıp
    yaramadığı, en iyi kısaltıcının hangisi olduğu değil. `turn`'ün cümle bölücüsü
    çağrılmıyor — o bir akış üzerinde çalışıyor ve buraya bir eşik getirirdi."""
    match = re.search(r"[.!?](\s|$)", text)
    return text[: match.end()].strip() if match else text.strip()


def _shorten_answers(history: Sequence[PromptMessage]) -> tuple[PromptMessage, ...]:
    """Eski asistan satırları ilk cümleye iner; son cevap tam kalır.

    **Bu ablasyonun kendi riski var ve ölçülmesinin sebebi o:** verinin ilk cümlede
    olması gayet mümkün ("Today is Sunday. You have no classes today"), yani kısaltmak
    veriyi hiç götürmeyebilir. Öyleyse `son-cevap`'la arasındaki fark, silmenin
    kaçınılmaz olup olmadığını söyler.
    """
    return _rewrite_older_answers(history, _first_sentence)


def _placeholder_answers(history: Sequence[PromptMessage]) -> tuple[PromptMessage, ...]:
    """Eski asistan satırları `(cevaplandı)` olur; son cevap tam kalır.

    `cevapsız` ile `kısa-cevap` arasındaki üçüncü nokta: içerik gidiyor ama **turun
    biçimi kalıyor** — soru soruldu, cevaplandı, sonra bu soru geldi. `söylenen`in
    sızıntısı burada da beklenmeli ve tam olarak o yüzden ölçülüyor.
    """
    return _rewrite_older_answers(history, lambda _: "(cevaplandı)")


SHAPES: dict[str, Callable[[Sequence[PromptMessage]], tuple[PromptMessage, ...]]] = {
    "cevapsız": _drop_answers,
    "söylenen": _mark_answers,
    "son-cevap": _last_answer_only,
    "kısa-cevap": _shorten_answers,
    "yer-tutucu": _placeholder_answers,
}
"""Geçmişin **biçimini** değiştiren ablasyonlar (Faz B/1 adayları).

Merdiven geçmişi kısaltıyor, bunlar kısaltmadan yeniden yazıyor: §2'nin bulgusu
"geçmiş" değil, geçmişteki asistan cevabının tool verisini taşıması.

Beşi bir eksen üzerinde duruyor — eski cevaptan **ne kadarı kalıyor**: `cevapsız` (hiç,
savın üst sınırı), `yer-tutucu` (yalnızca turun biçimi), `kısa-cevap` (ilk cümle),
`söylenen` (hepsi, ama söz diye işaretli), `son-cevap` (hiç, ama en yenisi tam).
Eksenin nerede kırıldığı, silmenin kaçınılmaz olup olmadığını söyler — ve o soru
sahibin itirazı: geçmiş modelin gözünde yok oluyor mu.

**Etiket `[araç]` izine değil, bütün asistan satırlarına vuruyor** ve sebebi ölçümde:
çöküş başladıktan sonra veriyi taşıyan cevapların `[araç]` satırı **yok** (mesaj 118'de
model çağırmadan "yüzde kırk" diyor). Yalnızca tool çağıran turun cevabını işaretlemek,
arızanın kendi ürettiği satırları atlardı.
"""


@dataclass(frozen=True, slots=True)
class Variant:
    """Bir ablasyon: öneğin hangi parçası çıkarılmış — ya da hangi biçimde yazılmış."""

    name: str
    summary: bool = True
    facts: bool = True
    history: int | None = None
    """Tutulan **en yeni** geçmiş mesaj sayısı; `None` hepsi."""
    shape: str | None = None
    """`SHAPES`'in anahtarı: geçmişin biçimini değiştiren dönüşüm. `None` dokunmaz."""


LADDER: tuple[Variant, ...] = (
    Variant("tam"),
    Variant("özetsiz", summary=False),
    Variant("olgusuz", facts=False),
    Variant("özetsiz+olgusuz", summary=False, facts=False),
    Variant("geçmişsiz", history=0),
    Variant("çıplak", summary=False, facts=False, history=0),
)
"""Ablasyon merdiveni. Sıra bilerek birikimli değil: önce tek tek çıkarılıyor, sonra
birlikte. Tek tek çıkarmak "hangisi" sorusunu, birlikte çıkarmak "yeter mi" sorusunu
cevaplıyor; yalnızca birikimli bir merdiven ikincisini birincisi sanırdı."""


BICIM: tuple[Variant, ...] = (
    Variant("tam"),
    Variant("cevapsız", shape="cevapsız"),
    Variant("kısa-cevap", shape="kısa-cevap"),
    Variant("yer-tutucu", shape="yer-tutucu"),
    Variant("son-cevap", shape="son-cevap"),
    Variant("söylenen", shape="söylenen"),
    Variant("geçmişsiz", history=0),
)
"""Biçim merdiveni (Faz B/1). İki ucu bilerek taşıyor: `tam` bugünkü üretim, `geçmişsiz`
§2'nin çağrıyı geri getirdiği bilinen nokta. Aradaki iki aday ancak bu ikisiyle birlikte
okunur — tek başına bir "çağırdı" satırı, geçmişin tamamını atmaktan ne kazandığını
söylemez."""


def sweep(lengths: Sequence[int]) -> tuple[Variant, ...]:
    """Geçmiş uzunluğu taraması: özet ve olgular yerinde, yalnızca geçmiş kısalıyor.

    Merdiven "hangi blok" sorusunu cevaplıyor ama geçmişi tek hamlede altmış mesajdan
    sıfıra indiriyor — çıkan cevap "geçmiş" olduğunda hâlâ **hangi** geçmiş olduğu
    bilinmiyor. Tarama onu soruyor: sınırın nereye düştüğü, o sınırdaki mesajların ne
    olduğuyla birlikte okunur.
    """
    return tuple(Variant(f"geçmiş-{n}", history=n) for n in lengths)


@dataclass(frozen=True, slots=True)
class Outcome:
    variant: str
    tokens: int
    """Öneğin jeton sayısı — sunucunun sayacından (Kural 10)."""
    attempt: _Attempt

    @property
    def called(self) -> str:
        call = self.attempt.call
        if call is None:
            return "—"
        args = " ".join(f"{k}={v!r}" for k, v in call.arguments.items())
        return f"`{call.name}`{' ' + args if args else ''}"


async def build_prefix(
    config: Config,
    db: Database,
    registry: Registry,
    rewound: Rewound,
    llm: LlamaCppLLM,
) -> tuple[str, Window, ContextBlock]:
    """Turun öneği — `turn/runner.py:_run`'ın yaptığının aynısı, aynı sırayla."""
    people = PeopleRepository(db)
    facts = FactRepository(db)
    window_builder = ContextWindow(
        llm=llm,
        messages=MessageRepository(db),
        summaries=SummaryRepository(db),
        recall=Recall(facts, people, max_facts=MAX_FACTS),
        reserved_output=RESERVED_OUTPUT_TOKENS,
        max_messages=MAX_HISTORY_MESSAGES,
    )
    system = _system(config, registry)
    # Kimlik `main.py`'nin iki yolundan biri; `person_id` yok (bkz. `_assumed_owner`).
    # Konuşmacı satırı `turn/runner.py:_speaker_line` ile aynı: yetkinin değeri.
    identity = Identity(
        authority=Authority.SAHIP if config.assume_owner else Authority.TANINMAYAN
    )
    context = ContextBlock(now=rewound.created_at, speaker=identity.authority.value)
    window = await window_builder.build(
        fixed_text=f"{system}\n{context.render()}\n{rewound.content}",
        person_id=identity.person_id,
    )
    return system, window, replace(context, facts=window.facts)


def messages_for(
    variant: Variant,
    system: str,
    window: Window,
    context: ContextBlock,
    user: str,
) -> tuple[PromptMessage, ...]:
    """Ablasyon uygulanmış mesaj dizisi. Dizinin **sırasını** yine `build_messages` kuruyor:
    burada yalnızca hangi bloğun verilmediği seçiliyor (§8.1 tek yerde)."""
    history = window.history
    if variant.history is not None:
        history = history[len(history) - variant.history :]
    if variant.shape is not None:
        # Kısaltmadan **sonra**: biçim, modele gerçekten giden satırlara uygulanmalı.
        history = SHAPES[variant.shape](history)
    return build_messages(
        system,
        context=context if variant.facts else replace(context, facts=None),
        user=user,
        summary=window.summary if variant.summary else None,
        history=history,
    )


async def run(
    config: Config,
    message_id: int,
    *,
    variants: Sequence[Variant],
    call_format: CallFormat,
    penalty: float,
    show_prefix: bool,
    out: Path | None,
) -> int:
    registry = builtin_registry(config)
    with tempfile.TemporaryDirectory(prefix="mayen-replay-") as tmp:
        snapshot = Path(tmp) / "replay.db"
        try:
            # Sahipliği almak Kural 1'in kendisi: `mayen` koşuyorsa burada durulur.
            with Database(config.db_path) as source:
                source.backup_to(snapshot)
        except DatabaseError as error:
            print(f"veritabanı açılamadı: {error}", file=sys.stderr)
            print(
                "mayen koşuyorsa önce durdurun (Kural 1: dosyanın tek sahibi var).",
                file=sys.stderr,
            )
            return 1
        with Database(snapshot) as db:
            rewound = rewind(db, message_id)
            if rewound.role != "user":
                print(
                    f"{message_id} numaralı mesaj `{rewound.role}`; tekrar oynatma bir"
                    " kullanıcı turunu ister.",
                    file=sys.stderr,
                )
                return 1
            sampling = Sampling(presence_penalty=penalty)
            async with httpx.AsyncClient(
                base_url=config.llm_url, timeout=TIMEOUT_SECONDS
            ) as http:
                llm = LlamaCppLLM(http, name="replay", sampling=sampling)
                if not await llm.health():
                    print(f"LLM servisi yanıt vermiyor: {config.llm_url}", file=sys.stderr)
                    return 1
                system, window, context = await build_prefix(config, db, registry, rewound, llm)
                outcomes = []
                for index, variant in enumerate(variants):
                    messages = messages_for(variant, system, window, context, rewound.content)
                    if show_prefix and index == 0:
                        _print_prefix(messages)
                    print(f"koşuluyor: {variant.name}", file=sys.stderr)
                    outcomes.append(
                        Outcome(
                            variant=variant.name,
                            tokens=await llm.count_tokens(
                                "\n".join(m.content for m in messages)
                            ),
                            attempt=await _attempt(
                                registry,
                                llm,
                                call_format,
                                messages,
                                max_corrections=MAX_CORRECTIONS,
                            ),
                        )
                    )
                report = _report(rewound, window, sampling, call_format, outcomes)
    if out is None:
        print(report)
    else:
        out.write_text(report, encoding="utf-8")
        print(f"rapor yazıldı: {out}", file=sys.stderr)
    return 0


def _print_prefix(messages: Sequence[PromptMessage]) -> None:
    """Modele giden dizinin tamamı. Kesilmiyor: bu aracın varlık sebebi öneğin **ne
    olduğunu** göstermek ve kısaltılan yer, bakılmayan yer olur."""
    for message in messages:
        print(f"----- {message.role} -----", file=sys.stderr)
        print(message.content, file=sys.stderr)


def _report(
    rewound: Rewound,
    window: Window,
    sampling: Sampling,
    call_format: CallFormat,
    outcomes: Sequence[Outcome],
) -> str:
    lines = [
        f"# Tekrar oynatma: mesaj {rewound.message_id}",
        "",
        f"- kullanıcı: {rewound.content!r}",
        f"- zaman: {rewound.created_at}",
        f"- çağrı biçimi: {call_format.value}",
        f"- `presence_penalty`: {sampling.presence_penalty}",
        f"- özet: {len(window.summary or '')} karakter",
        f"- olgular: {len((window.facts or '').splitlines()) - 2 if window.facts else 0} satır",
        f"- geçmiş: {len(window.history)} mesaj (kırpılan: {window.trimmed})",
        "",
        "Tek turluk üretim: ajan döngüsü koşmuyor, tool gövdesi çalışmıyor. Ölçülen tek şey"
        " **çağrı üretildi mi**.",
        "",
        "| ablasyon | önek jetonu | çağrı | çıktı |",
        "|---|---:|---|---|",
    ]
    for outcome in outcomes:
        text = outcome.attempt.output.strip().replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {outcome.variant} | {outcome.tokens} | {outcome.called} | {text[:120]} |"
        )
    return "\n".join(lines)


def _system(config: Config, registry: Registry) -> str:
    """Sistem promptu — `main.py:_system` ile aynı üç parça, aynı sırayla."""
    if config.role_path is None:
        raise ConfigError("Rol dosyası verilmedi: MAYEN_ROLE_PATH")
    rule = None
    if config.language_rule_path is not None:
        rule = load_role(config.language_rule_path)
    return system_prompt(
        registry, CALL_FORMAT, role=load_role(config.role_path), language_rule=rule
    )


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evals.replay", description="Bir turu veritabanından yeniden oynatır"
    )
    parser.add_argument(
        "--mesaj", type=int, required=True, help="Yeniden oynatılacak kullanıcı mesajının id'si"
    )
    parser.add_argument(
        "--ceza",
        type=float,
        default=HISTORICAL_PRESENCE_PENALTY,
        help="`presence_penalty`. Varsayılan 1.5 — o turda yürürlükte olan değer."
        " 0 vermek A4'ün değişikliğini ölçer",
    )
    parser.add_argument(
        "--sade",
        action="store_true",
        help="Yalnızca `tam` koşulsun; ablasyon merdiveni koşulmasın",
    )
    parser.add_argument(
        "--gecmis",
        type=int,
        action="append",
        help="Merdiven yerine geçmiş uzunluğu taraması: tutulacak en yeni mesaj sayısı;"
        " birden çok kez verilebilir",
    )
    parser.add_argument(
        "--bicim",
        action="store_true",
        help="Merdiven yerine biçim ablasyonları: geçmiş kısalmıyor, asistan satırları"
        " çıkarılıyor ya da `[söylenen]` diye etiketleniyor (Faz B/1)",
    )
    parser.add_argument(
        "--onek-yaz",
        dest="show_prefix",
        action="store_true",
        help="Modele giden mesaj dizisinin tamamını stderr'e yazar",
    )
    parser.add_argument("--out", type=Path, help="Raporun yazılacağı dosya")
    args = parser.parse_args(argv)

    try:
        config = load()
    except ConfigError as error:
        print(f"yapılandırma okunamadı: {error}", file=sys.stderr)
        return 1
    if args.gecmis:
        variants: tuple[Variant, ...] = sweep(sorted(args.gecmis))
    elif args.bicim:
        variants = BICIM
    else:
        variants = LADDER[:1] if args.sade else LADDER
    return await run(
        config,
        args.mesaj,
        variants=variants,
        call_format=CALL_FORMAT,
        penalty=args.ceza,
        show_prefix=args.show_prefix,
        out=args.out,
    )


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

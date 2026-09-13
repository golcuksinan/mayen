"""Ölçüm sonuçlarının toplanması ve raporu (§18 Faz 0 çıktısı).

**Tek bir "doğruluk" sayısı üretilmiyor** (§17.1): tool seçimi, argüman doğruluğu ve
halüsinasyon sayaçları ayrı ayrı duruyor. Üçünü eritmek, hangi ekseni bozduğunu
göstermeyen bir yüzde verirdi — ve bu ölçümün varlık sebebi tam da o ayrımı görmek.

**Eksen kırılımı da ayrı** (§18'in altı zorluk ekseni). Toplamda eşit görünen iki biçim,
serbest metin ekseninde birbirinden ayrılabilir; karar oradan çıkar.

**Bağlam kırılımı ayrı** (2026-08-13). Geçmişli senaryolarda ölçülen şey aynı — tool
seçimi — ama koşul farklı: modelin öneğinde kaç geçmiş tur var. Kısa ve uzun geçmiş tek
ortalamada eritilirse, tuzağın uzunlukla büyüyüp büyümediği görünmez ve düzeltmenin
işe yarayıp yaramadığı da ölçülemez.

**Üçüncü halüsinasyon sayacı dar adıyla duruyor** (Kural 14): ölçülen şey "desteksiz
sayı" — yanıtta geçip ne tool sonucunda ne kullanıcı turunda bulunan sayılar (bkz.
`runner._answer`). Yalnızca hazır sonucu olan senaryolarda koşuyor, o yüzden paydası ayrı
yazılıyor. "Halüsinasyon yok" diye özetlemek, ölçülmeyen dilimi ölçülmüş gibi gösterirdi.

**İlk iki halüsinasyon sayacı adının yanında sınırını taşıyor** (P26, Kural 14). İkisi de
gramerin ürettiği literal alternatiflerle sınırlı: `uydurulan tool` yapısal olarak sıfır ve
o sıfır modelin değil gramerin ölçüsü. Sütun başlığı bunu yazmadığı sürece bir sonuç gibi
okunuyordu — dört rapor boyunca öyle okundu.

**Yargılanmayan yanıtlar ayrı bölümde** (P26). Çağrı üretilmeyen senaryolarda modelin düz
metni kaydediliyor ama hiçbir paydaya girmiyor; kanıt ile ölçü aynı yerde durursa ölçmediğin
şeye sayı vermiş olursun.

**Her orana güven aralığı eşlik ediyor** (P25.2, Kural 14). n=50'de %94 ile %92 arasındaki
fark gürültünün içindedir ve aralık yazılmadığı sürece bu cümle bir sıralama gibi okunur —
P7'de tam olarak öyle okundu. Aralık Wilson; gerekçesi `wilson()`'da.

**İkinci adım ayrı bölüm** (P25.2). Zincirin ikinci halkası ile ilk halkasını tek doğruluk
yüzdesinde eritmek, `gec-04` gibi "ilk adımı doğru, ikinci adımı yanlış" bir hatayı yarı
doğru gösterirdi.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from statistics import mean

from evals.runner import (
    LONG_CONTEXT_TOKENS,
    MAX_CORRECTIONS,
    Context,
    Prefix,
    ScenarioResult,
)
from evals.scenarios import Kind
from mayen.adapters.llamacpp import Sampling

Z = 1.96
"""%95 güven aralığının normal yaklaşımı. Bir ölçüm parametresi, doküman kararı değil."""


def wilson(hits: int, total: int, z: float = Z) -> tuple[float, float]:
    """Bir oranın %95 güven aralığı (Wilson).

    **Normal yaklaşım (`p ± z·√(p(1-p)/n)`) kullanılmıyor**: bu ölçümün ilgilendiği yer
    tam olarak oranın uçlara yakın olduğu bölge — %94, %100 — ve orada normal yaklaşım
    1'i aşan ya da genişliği sıfır olan aralıklar üretiyor. `n=50, p=1.0`'da normal
    yaklaşım "[100, 100]" der; Wilson "[93, 100]" der ve doğrusu odur.

    Neden hiç aralık yazılmadan yaşanamayacağı P7'de görüldü: "CLI 94, JSON 92" farkı
    n=50'de gürültünün içinde kalıyor ve o cümle bir sıralama gibi okunuyordu. Karar
    maliyete dayandırılmıştı, yani doğru verilmişti — ama rapor bunu okuyana söylemiyordu.
    """
    if total == 0:
        raise ValueError("boş paydanın güven aralığı yok")
    p = hits / total
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    spread = z * sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return max(0.0, center - spread), min(1.0, center + spread)


def _with_interval(hits: int, total: int) -> str:
    low, high = wilson(hits, total)
    return f"{hits / total:.0%} [{low:.0%}–{high:.0%}]"


@dataclass(frozen=True, slots=True)
class Summary:
    """Bir (model × çağrı biçimi) koşusunun toplamı."""

    label: str
    count: int
    """Ölçülebilmiş senaryo sayısı — servis hatasıyla düşenler hariç."""
    errors: int
    """Ölçülemeyen senaryo sayısı. Sıfır değilse koşu **eksiktir** ve rapor bunu yazar."""
    tool_accuracy: float
    tool_interval: tuple[float, float]
    """Tool doğruluğunun %95 güven aralığı (Wilson). Küçük farkların sıralama gibi
    okunmasını mekanik olarak engelliyor — Kural 14'ün ruhu."""
    step2_correct: int
    step2_run: int
    """İkinci adımı koşulan senaryo sayısı — ikinci adım doğruluğunun paydası."""
    argument_accuracy: float | None
    """Tool'u doğru seçilen çağrılar içinde argümanı da doğru olanların payı. Tool'u doğru
    seçilen hiç çağrı yoksa tanımsız."""
    hallucinated_tools: int
    hallucinated_arguments: int
    unsupported_numbers: int
    unsupported_quotes: int
    """Desteksiz alıntı sayısı (P26). Paydası `answered` **değil**: çağrısız senaryoların
    yargılanmayan yanıtları da taranıyor, o yüzden ham sayı olarak duruyor."""
    answered: int
    """Yargılanan yanıt turu sayısı — desteksiz sayı sayacının paydası. Kaydedilen ama
    yargılanmayan yanıtlar (çağrısız senaryolar, P26) buraya girmiyor."""
    ungraded_answers: int
    """Kaydedilen ama hiçbir paydaya girmeyen yanıt sayısı (P26)."""
    corrections: int
    mean_tokens: float
    mean_seconds: float
    mean_ttft: float
    """İlk token'a kadar geçen sürenin ortalaması (§6, §19.4)."""


def measured(results: Sequence[ScenarioResult]) -> list[ScenarioResult]:
    """Ölçülebilmiş satırlar. Servis hatasıyla düşen senaryo hiçbir doğruluk paydasına
    girmiyor — modelin yanlışı değil, ölçümün eksiği (bkz. `runner.run_all`)."""
    return [r for r in results if r.error is None]


def summarize(label: str, results: Sequence[ScenarioResult]) -> Summary:
    if not results:
        raise ValueError("boş sonuç kümesi özetlenemez")
    ok = measured(results)
    if not ok:
        raise ValueError("hiçbir senaryo ölçülemedi: özetlenecek sayı yok")
    graded = [r for r in ok if r.arguments_correct is not None]
    return Summary(
        label=label,
        count=len(ok),
        errors=len(results) - len(ok),
        tool_accuracy=_ratio(sum(r.tool_correct for r in ok), len(ok)),
        tool_interval=wilson(sum(r.tool_correct for r in ok), len(ok)),
        step2_correct=sum(bool(r.step2_tool_correct) for r in ok),
        step2_run=sum(r.step2_run for r in ok),
        argument_accuracy=(
            _ratio(sum(bool(r.arguments_correct) for r in graded), len(graded))
            if graded
            else None
        ),
        hallucinated_tools=sum(r.unknown_tool for r in ok),
        hallucinated_arguments=sum(r.unknown_argument for r in ok),
        unsupported_numbers=sum(len(r.unsupported_numbers) for r in ok),
        unsupported_quotes=sum(len(r.unsupported_quotes) for r in ok),
        answered=sum(r.answer_graded for r in ok),
        ungraded_answers=sum(r.answer is not None and not r.answer_graded for r in ok),
        corrections=sum(r.corrections for r in ok),
        mean_tokens=mean(r.tokens for r in ok),
        mean_seconds=mean(r.seconds for r in ok),
        mean_ttft=mean(r.ttft for r in ok),
    )


def _ungraded(results: Sequence[ScenarioResult]) -> list[ScenarioResult]:
    """Kaydedilen ama yargılanmayan yanıtlar (P26)."""
    return [r for r in measured(results) if r.answer is not None and not r.answer_graded]


def _ratio(hits: int, total: int) -> float:
    return hits / total


SAMPLERS = (
    "temperature",
    "top_k",
    "top_p",
    "min_p",
    "repeat_penalty",
    "presence_penalty",
    "frequency_penalty",
)
"""Rapora yazılan örnekleme ayarları. Hepsi değil — sunucu kırktan fazla alan bildiriyor
ve gerisi bu ölçümde sabit. Bunlar, modelden modele farklı olduğu **görülmüş** olanlar:
`presence_penalty` 35B'de 1.5, 27B'de 0'dı ve eşitlenmediğinde karşılaştırılan şey model
değil bayrak seti olur."""


GRAMMAR_BOUND_COUNTERS = (
    "**`uydurulan tool` ve `uydurulan argüman` sütunları gramerle sınırlıdır: modelin"
    " değil, gramerin ölçüsüdürler.** GBNF tool adlarını birebir literal alternatif"
    " olarak sayıyor, yani defterde olmayan bir ad **üretilemez** ve bu sütun yapısal"
    ' olarak sıfırdır. Sıfır burada "model tool uydurmuyor" demek değil, "gramer'
    ' çalışıyor" demektir (Kural 14). `uydurulan argüman` yalnızca tek bir yoldan'
    " sıfırdan farklı çıkabiliyor — liste değerinden (`cli-item`) sonra yazılan bayrak"
    " görünümlü jeton; bkz. `tests/test_agent_calls.py`. **Üretimdeki halüsinasyon başka"
    " bir şeydir** ve `halusinasyon` kümesi onu tool seçimi üzerinden ölçüyor (P26)."
)
"""Kural 14'ün rapor tarafı. Sabit: bir testin varlığını sınayabilmesi için tek kopya."""


def _server_block(
    server: Mapping[str, object] | None, sampling: Sampling | None = None
) -> list[str]:
    """`/props`'tan okunan ayarlar. Sunucu söylemiyorsa blok hiç yazılmıyor — boş bir
    tablo, ayarların ölçülmüş ama önemsiz olduğu izlenimi verirdi (Kural 14).

    **İki sütun, çünkü ölçülen şey ikisinin farkı** (Faz A/A4): sunucunun varsayılanı ve
    adaptörün istekte gönderdiği. Bu liste bu ayrışmayı yıllardır **biliyordu** —
    `SAMPLERS`'ın gerekçesi `presence_penalty`'nin iki model arasında farklı olduğunu
    yazıyor — ama farkı yalnızca iki raporu yan yana koyan biri görebiliyordu. Artık tek
    raporda ve ezilen her satır adıyla işaretli.
    """
    if server is None:
        return []
    settings = server.get("default_generation_settings")
    params = settings.get("params") if isinstance(settings, dict) else None
    lines = [
        "## Sunucu ayarları",
        "",
        "Başlatma komutundan kopyalanmadı, koşu anında `/props`'tan **okundu**: elle"
        " yazılan bir bayrak listesi, komut değiştiğinde raporu sessizce yalancı yapar.",
        "",
        f"- model: `{server.get('model_path')}` ({server.get('model_ftype')})",
    ]
    if isinstance(settings, dict):
        lines.append(f"- `n_ctx`: {settings.get('n_ctx')}")
    if isinstance(params, dict):
        lines += ["", *_sampling_table(params, sampling), ""]
    return [*lines, ""]


def _sampling_table(params: Mapping[str, object], sampling: Sampling | None) -> list[str]:
    """Sunucunun varsayılanı ile isteğin gönderdiği, yan yana."""
    if sampling is None:
        shown = ", ".join(f"`{name}`={params.get(name)}" for name in SAMPLERS)
        return [
            f"- sunucunun varsayılan örneklemesi: {shown}",
            "- adaptörün istekte ne gönderdiği bu koşuda kaydedilmedi; iki taraf"
            " ayrışmışsa rapor bunu gösteremez.",
        ]
    sent = sampling.body()
    rows = [
        "| örnekleme | sunucu (`/props`) | istek (adaptör) |",
        "|---|---:|---:|",
    ]
    for name in sorted(sent):
        default = params.get(name, "—")
        mark = "" if _same(default, sent[name]) else " **←**"
        rows.append(f"| `{name}` | {default} | {sent[name]}{mark} |")
    return [
        *rows,
        "",
        "Sağ sütun her istekte gönderiliyor ve solu **ezer**; `←` işaretli satırlar"
        " sunucunun bayrağının artık okunmadığı yerler. Sunucudan gelen tek şey `n_ctx`.",
    ]


def _same(left: object, right: object) -> bool:
    """Sunucu her sayıyı float bildiriyor (`1.0` ile `1`), yani `==` biçim farkına takılır."""
    if isinstance(left, int | float) and isinstance(right, int | float):
        return abs(float(left) - float(right)) < 1e-6
    return left == right


def _context_size(server: Mapping[str, object] | None) -> int | None:
    """Sunucunun bildirdiği `n_ctx`. Yapılandırmadan değil `/props`'tan — Kural 10'un ve
    §11.1'in aynı gerekçesi: bağlam boyu sorulur, varsayılmaz."""
    if server is None:
        return None
    settings = server.get("default_generation_settings")
    size = settings.get("n_ctx") if isinstance(settings, dict) else None
    return size if isinstance(size, int) else None


def _fill_lines(
    runs: Sequence[tuple[str, Sequence[ScenarioResult]]],
    server: Mapping[str, object] | None,
) -> list[str]:
    """Kovaların **gerçek** doluluğu (P27).

    Bir kovanın adı değil boyu okunmalı: "uzun geçmiş" bugüne kadar `n_ctx`'in ~%6'sını
    dolduran bir bloğa deniyordu ve rapor bunu okuyana hiç söylemiyordu (Kural 14).
    """
    size = _context_size(server)
    lines = [
        "Kovaların gerçek doluluğu (ortalama jeton"
        + (f", ve `n_ctx`={size} içindeki payı):" if size else "):"),
        "",
    ]
    for label, results in runs:
        parts = []
        for context in Context:
            subset = [r for r in measured(results) if r.context is context]
            if not subset:
                continue
            average = mean(r.context_tokens for r in subset)
            share = f" (%{100 * average / size:.1f})" if size else ""
            parts.append(f"{context.value} ~{average:.0f} jeton{share}")
        if parts:
            lines.append(f"- **{label}**: " + ", ".join(parts))
    return [*lines, ""]


def _prefix_block(
    runs: Sequence[tuple[str, Sequence[ScenarioResult]]], role_paths: Sequence[Path]
) -> list[str]:
    """Hangi koşunun hangi önekle kurulduğu (P27).

    **Rol dosyasının yolu da yazılıyor**, çünkü içeriği sonucu etkiliyor: dosya
    değiştiğinde aynı komut başka bir sınav koşar ve rapor bunu okuyana söylemezse fark
    sessizce modele yazılır (`_server_block`'un aynı gerekçesi).
    """
    used = {r.prefix for _, results in runs for r in results}
    if used == {Prefix.OLCUM}:
        return []
    lines = [
        "## Önek",
        "",
        "Ölçümün modele gönderdiği mesaj dizisi iki türlü kurulabiliyor ve **hangisi**"
        " olduğu sonucu değiştirir (P27):",
        "",
        f"- **{Prefix.OLCUM.value}** — `docs/faz2-olcum.md`'den beri kullanılan dizi:"
        " çağrı yönergesi + katalog, tek satırlık bağlam, geçmiş. Rol metni, `[özet]`"
        " bloğu ve olgular **yok**.",
        f"- **{Prefix.URETIM.value}** — `turn/runner.py`'nin modele gerçekten gönderdiği"
        " dizi; `agent.prompt.build_messages` ile kuruluyor, ikinci bir kopya yok.",
        "",
    ]
    if role_paths:
        lines.append(
            "Rol metni: " + ", ".join(f"`{path}`" for path in role_paths) + " —"
            " **içeriği sonucu ölçülebilir biçimde etkiliyor** (`docs/faz6-onek.md`),"
            " o yüzden dosya adı raporda duruyor. Birden çok verilmişse her biri ayrı"
            " kolon ve etikette `rol(ad)` diye yazılı."
        )
        lines.append("")
    return lines


def render(
    runs: Sequence[tuple[str, Sequence[ScenarioResult]]],
    *,
    server: Mapping[str, object] | None = None,
    sampling: Sampling | None = None,
    role_paths: Sequence[Path] = (),
) -> str:
    """Markdown rapor. `runs`: (etiket, sonuçlar) çiftleri — her biri bir model × biçim.

    `server` verilirse sunucunun **kendi bildirdiği** ayarları rapora yazılır. Elle
    kopyalanan bir bayrak listesi değil, bilerek: `docs/faz2-olcum.md`'nin başındaki blok
    elle yazılmıştı ve bir koşuda başlatma komutu değişirse rapor sessizce yalan söylerdi.
    Örnekleme ayarları modelden modele farklı olduğunda karşılaştırılan şey model değil
    bayrak seti olur — bu blok o farkın görülebildiği tek yer.
    """
    lines = [
        "# Çağrı biçimi ve tool modu ölçümü",
        "",
        f"Düzeltme turu tavanı: {MAX_CORRECTIONS}. Karşılaştırma birebir; tek istisna,"
        " cümle sonu noktalamasının iki tarafta da atılması. Büyük/küçük harf katlaması"
        " yok — Türkçe'de `I`/`ı` üzerinde yanlış çalışır.",
        "",
        "Tool doğruluğunun yanındaki köşeli parantez **%95 Wilson güven aralığı**."
        " Aralıkları çakışan iki koşu arasında sıralama yapmak, gürültüyü sonuç diye"
        " okumaktır: n=50'de %94 ile %92 arasındaki fark böyle bir farktır (P7).",
        "",
        *_server_block(server, sampling),
        *_prefix_block(runs, role_paths),
        "## Toplam",
        "",
        GRAMMAR_BOUND_COUNTERS,
        "",
        "| koşu | n | tool doğruluğu [%95] | argüman doğruluğu | 2. adım (n) |"
        " uydurulan tool (gramerle sınırlı) | uydurulan argüman (gramerle sınırlı) |"
        " desteksiz sayı (n) | desteksiz alıntı | düzeltme turu |"
        " ort. token | ort. TTFT | ort. sn |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, results in runs:
        s = summarize(label, results)
        argument = "—" if s.argument_accuracy is None else f"{s.argument_accuracy:.0%}"
        step2 = (
            "—"
            if not s.step2_run
            else f"{_with_interval(s.step2_correct, s.step2_run)} ({s.step2_run})"
        )
        lines.append(
            f"| {s.label} | {s.count} |"
            f" {_with_interval(sum(r.tool_correct for r in measured(results)), s.count)} |"
            f" {argument} |"
            f" {step2} |"
            f" {s.hallucinated_tools} | {s.hallucinated_arguments} |"
            f" {s.unsupported_numbers} ({s.answered}) | {s.unsupported_quotes} |"
            f" {s.corrections} |"
            f" {s.mean_tokens:.0f} | {s.mean_ttft:.2f} | {s.mean_seconds:.2f} |"
        )

    lines += ["", "## Eksen kırılımı (tool doğruluğu)", ""]
    header = "| koşu | " + " | ".join(kind.value for kind in Kind) + " |"
    lines += [header, "|---" * (len(Kind) + 1) + "|"]
    for label, results in runs:
        cells = []
        for kind in Kind:
            subset = [r for r in measured(results) if r.kind is kind]
            cells.append(
                "—"
                if not subset
                else f"{_ratio(sum(r.tool_correct for r in subset), len(subset)):.0%}"
            )
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    if any(r.context is not Context.YOK for _, results in runs for r in results):
        lines += ["", "## Bağlam kırılımı (tool doğruluğu)", ""]
        lines += [
            f'Kova sınırı: **{LONG_CONTEXT_TOKENS} jeton** ve üstü "uzun" (P27). Sayan'
            " taraf sunucunun kendi sayacı, tahmin değil (Kural 10); ölçülen şey öneğin"
            " değişken kısmı — özet, geçmiş, bağlam bloğu ve güncel tur. Bu bir rapor"
            " kovası, sistemde bir eşik değil (`evals/runner.py`).",
            "",
            "Eşik jetona 2026-08-15'te geçti. Öncesinde tur sayısıydı ve `uzun` kovası"
            " 5 turluk ~247 karakterlik bir bloğu adlandırıyordu; modele giden şey ise"
            " tur değil jeton. Aşağıdaki doluluk satırı kovanın **gerçek** boyunu yazıyor,"
            " yani eşik yanlış seçilmişse okuyan görüyor.",
            "",
        ]
        header = "| koşu | " + " | ".join(c.value for c in Context) + " |"
        lines += [header, "|---" * (len(Context) + 1) + "|"]
        for label, results in runs:
            cells = []
            for context in Context:
                subset = [r for r in measured(results) if r.context is context]
                cells.append(
                    "—"
                    if not subset
                    else f"{_ratio(sum(r.tool_correct for r in subset), len(subset)):.0%}"
                    f" ({len(subset)})"
                )
            lines.append(f"| {label} | " + " | ".join(cells) + " |")
        lines.append("")
        lines += _fill_lines(runs, server)

    if any(r.step2_run for _, results in runs for r in results):
        lines += ["", "## İkinci adım", ""]
        lines += [
            "Tool sonucu geri beslendikten sonraki adım (P25.2). Zincirin ikinci halkası"
            " bugüne kadar hiç ölçülmemişti; `Step2.expected` `None` olan satırlarda doğru"
            " davranış **çağrı yazmamaktır** — o satırlar olmadan bu sayaç, fazla çağrıyı"
            " iyileşme diye raporlardı.",
            "",
        ]
        for label, results in runs:
            wrong = [r for r in measured(results) if r.step2_run and not r.step2_tool_correct]
            if not wrong:
                continue
            lines.append(f"**{label}** — ikinci adımda düşenler:")
            lines.append("")
            for result in wrong:
                got = "çağrı yok" if result.step2_call is None else result.step2_call.name
                lines.append(f"- `{result.scenario_id}`: 2. adımda `{got}`")
            lines.append("")

    if any(r.error for _, results in runs for r in results):
        lines += ["", "## Ölçülemeyen senaryolar", ""]
        lines += [
            "Servis iki denemede de düştü. Bu satırlar **hiçbir doğruluk paydasına"
            " girmiyor**: modelin yanlışı değil, ölçümün eksiği. Yanlış cevap sayılsalardı"
            " model servisin kopmasından sorumlu tutulurdu; hiç yazılmasalardı payda"
            " sessizce küçülür ve rapor eksikliğini gizlerdi (Kural 13, Kural 14).",
            "",
            "**Bir sayı burada görünüyorsa o koşu eksiktir ve öyle okunmalıdır.**",
            "",
        ]
        for label, results in runs:
            broken = [r for r in results if r.error]
            if not broken:
                continue
            lines.append(f"**{label}** — {len(broken)}/{len(results)}:")
            lines.append("")
            for result in broken:
                lines.append(f"- `{result.scenario_id}`: {result.error}")
            lines.append("")

    lines += [
        "",
        "## Sayacın kapsamı",
        "",
        "§17.1'in üçüncü halüsinasyon sayacı yalnızca **sayısal** iddia üzerinden"
        " ölçülüyor: tool sonucu geri besleniyor, yanıttaki her sayı sonuçta ve kullanıcı"
        " turunda aranıyor, bulunmayan desteksiz sayılıyor. Parantez içindeki sayı"
        " paydadır — hazır sonucu olan ve çağrısı doğru üretilen senaryolar. Serbest"
        " cümledeki iddialar mekanik olarak ölçülemiyor; bir hakem modeli kendi"
        " halüsinasyonunu ölçüme karıştırırdı.",
        "",
    ]
    for label, results in runs:
        claimed = [r for r in results if r.unsupported_numbers]
        if not claimed:
            continue
        lines.append(f"**{label}** — desteksiz sayı geçen senaryolar:")
        lines.append("")
        for result in claimed:
            numbers = ", ".join(f"`{n}`" for n in result.unsupported_numbers)
            lines.append(f"- `{result.scenario_id}`: {numbers} — yanıt: `{result.answer}`")
        lines.append("")

    if any(r.unsupported_quotes for _, results in runs for r in results):
        lines += [
            "Dördüncü sayaç — **desteksiz alıntı** (P26): yanıtta tırnak içinde geçip ne"
            " tool sonucunda, ne kullanıcı turunda, ne de geçmişte bulunan metin. Sayının"
            " eşi ve onun kadar dar; tırnaksız serbest cümledeki iddia hâlâ ölçülemiyor.",
            "",
        ]
        for label, results in runs:
            quoted = [r for r in results if r.unsupported_quotes]
            if not quoted:
                continue
            lines.append(f"**{label}** — desteksiz alıntı geçen senaryolar:")
            lines.append("")
            for result in quoted:
                items = ", ".join(f"`{q}`" for q in result.unsupported_quotes)
                lines.append(f"- `{result.scenario_id}`: {items}")
            lines.append("")

    if any(_ungraded(results) for _, results in runs):
        lines += [
            "## Mekanik olarak yargılanmadı",
            "",
            "Çağrı üretilmeyen senaryolarda modelin düz metni **kaydediliyor ama"
            ' yargılanmıyor** (P26). Geri beslenecek bir tool sonucu yok, yani "bu cümle'
            ' destekli mi" sorusunun hakem modeli olmadan mekanik cevabı da yok. Bu'
            " metinler hiçbir doğruluk paydasına girmiyor; buraya kanıt olarak yazılıyorlar"
            " (Kural 13), çünkü üretimdeki halüsinasyonun göründüğü yer tam olarak burası."
            " Senaryonun **düşüp düşmediği** bu metinden değil, çağrının yokluğundan"
            " okunuyor.",
            "",
        ]
        for label, results in runs:
            ungraded = _ungraded(results)
            if not ungraded:
                continue
            lines.append(f"**{label}** — {len(ungraded)} yanıt:")
            lines.append("")
            for result in ungraded:
                text = (result.answer or "").replace("\n", " ")[:200]
                lines.append(f"- `{result.scenario_id}`: `{text}`")
            lines.append("")

    lines += [
        "## Başarısız senaryolar",
        "",
    ]
    for label, results in runs:
        # İkinci adımda düşen senaryo da buraya giriyor: `failures` onun gerekçesini
        # taşıyor ("2. adım: …") ve filtre yalnızca ilk adıma bakarsa o metin hiç
        # yazılmaz — Kural 13'ün rapor tarafı.
        failed = [
            r
            for r in measured(results)
            if not r.tool_correct
            or r.arguments_correct is False
            or r.step2_tool_correct is False
            or r.step2_arguments_correct is False
        ]
        lines.append(f"### {label} — {len(failed)}/{len(results)}")
        lines.append("")
        if not failed:
            lines += ["Yok.", ""]
            continue
        for result in failed:
            lines.append(
                f"- `{result.scenario_id}` ({result.kind.value}): "
                + "; ".join(result.failures)
                + f" — çıktı: `{result.output.splitlines()[0][:120] if result.output else ''}`"
            )
        lines.append("")
    return "\n".join(lines)

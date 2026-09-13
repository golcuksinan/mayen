"""Ölçümü koşan komut: `uv run python -m evals [--out rapor.md]`.

Model adı sunucudan değil komut satırından alınıyor: `llama-server` tek model servis
ediyor ve raporun sütun başlığı, hangi `gguf`'un ölçüldüğünü okuyanın anlayacağı ad
olmalı — dosya yolu değil.
"""

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx

from evals.report import render
from evals.runner import Prefix, run_all
from evals.scenarios import (
    APPROVAL_SCENARIOS,
    CONTROL_SCENARIOS,
    HALLUCINATION_SCENARIOS,
    HISTORY_SCENARIOS,
    LONG_RESULT_SCENARIOS,
    MEMORY_SCENARIOS,
    ROBUST_SCENARIOS,
    SCENARIOS,
    STEP2_SCENARIOS,
    Scenario,
)
from mayen.adapters.llamacpp import LlamaCppLLM
from mayen.agent.calls import CallFormat
from mayen.agent.prompt import load_role
from mayen.config import ConfigError, load
from mayen.main import CALL_FORMAT
from mayen.tools.catalog import builtin_registry

TIMEOUT_SECONDS = 300.0
"""Ölçüm bütçesi tur akışının bütçesi değil: burada tek bir yavaş çağrı koşuyu bozmasın
diye geniş tutuluyor (§19.4'ün gecikme hedefiyle ilgisi yok)."""

SETS: dict[str, Sequence[Scenario]] = {
    "altin": SCENARIOS,
    "kontrol": CONTROL_SCENARIOS,
    "adim2": STEP2_SCENARIOS,
    "saglamlik": ROBUST_SCENARIOS,
    "uzun": LONG_RESULT_SCENARIOS,
    "halusinasyon": HALLUCINATION_SCENARIOS,
    "bellek": MEMORY_SCENARIOS,
    "onay": APPROVAL_SCENARIOS,
}
"""Adıyla koşulabilen kümeler. `gecmis` burada **yok**: iki kez, iki farklı geçmiş
biçimiyle koştuğu için tek bir küme değil bir koşu tarifi (bkz. `_runs`)."""

PREFIXES: dict[str, Prefix] = {"bellek": Prefix.URETIM, "onay": Prefix.URETIM}
"""Kümenin **zorunlu** öneği (P27). `bellek` kümesinin senaryoları özet ve olgu blokları
taşıyor; ölçüm öneğinde o blokların gideceği bir yer yok, yani küme ölçüm öneğiyle
koşulursa sessizce başka bir sınav olur. Geri kalan kümeler `--onek` ile her iki dünyada
da koşulabiliyor ve varsayılan `ÖLÇÜM` — eski raporlar onunla karşılaştırılabilsin diye."""


def _runs(
    names: Sequence[str], chosen: Sequence[Prefix] = (Prefix.OLCUM,)
) -> list[tuple[Sequence[Scenario], bool, Prefix, str]]:
    """Hangi küme, hangi geçmiş biçimiyle, hangi önekle, hangi etiket ekiyle koşacak.

    **Önek birden çok verilebiliyor** (P27): asıl soru "üretimin öneği eski sayıları
    oynatıyor mu" ve bunun cevabı iki kolonun **aynı raporda** yan yana durmasıyla
    okunur. İki ayrı dosya, aynı gün aynı sunucuyla koşulduğunu okuyana kanıtlamaz.
    """
    runs: list[tuple[Sequence[Scenario], bool, Prefix, str]] = []
    forced_done: set[str] = set()
    for prefix in chosen:
        for name in names:
            if name == "gecmis":
                # Karşılaştırılan şey iki *model* değil, aynı modelin iki geçmişi — izli
                # ve izsiz. Tek koşu, 2026-08-13 düzeltmesinin işe yarayıp yaramadığı
                # sorusunu cevapsız bırakırdı.
                runs.append((HISTORY_SCENARIOS, True, prefix, " × geçmiş(izli)"))
                runs.append((HISTORY_SCENARIOS, False, prefix, " × geçmiş(izsiz)"))
            else:
                suffix = "" if name == "altin" else f" × {name}"
                forced = PREFIXES.get(name)
                if forced is not None:
                    # Öneği sabit küme **bir kez** koşuyor, seçilen önekten bağımsız:
                    # `prefix`e eşitlik aransaydı tek önekli koşuda küme sessizce
                    # atlanır ve rapor boş çıkardı (2026-08-15'te tam olarak oldu).
                    if name in forced_done:
                        continue
                    forced_done.add(name)
                runs.append((SETS[name], True, forced or prefix, suffix))
    return runs


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evals", description="Faz 0 çağrı biçimi ölçümü")
    parser.add_argument("--model", required=True, help="Rapora yazılacak model adı")
    parser.add_argument("--out", type=Path, help="Raporun yazılacağı dosya")
    parser.add_argument(
        "--kume",
        action="append",
        choices=[*SETS, "gecmis"],
        help="Koşulacak senaryo kümesi; birden çok kez verilebilir (varsayılan: altin)."
        " `gecmis` her biçim için iki kez koşar — tool izi olan ve olmayan geçmişle"
        " (2026-08-13 düzeltmesinin ölçümü)",
    )
    parser.add_argument(
        "--rol",
        action="append",
        type=Path,
        help="Rol metni dosyası; birden çok kez verilebilirse her biri ayrı kolon olur"
        " (P27 sonrası: rol metni sonucu ölçülebilir biçimde değiştiriyor). Verilmezse"
        " MAYEN_ROLE_PATH kullanılır. Yalnızca üretim öneğinde etkili",
    )
    parser.add_argument(
        "--dil-kurali",
        action="append",
        type=Path,
        dest="dil_kurali",
        help="Öneğin en sonuna, üretimin hemen önüne konacak dil kuralı dosyası; birden"
        " çok kez verilebilir ve her biri ayrı kolon olur. Kuralsız kol her zaman koşar,"
        " yoksa karşılaştırılacak bir taban kalmazdı. Yalnızca üretim öneğinde etkili",
    )
    parser.add_argument(
        "--onek",
        action="append",
        choices=[p.name.lower() for p in Prefix],
        help="Hangi önek kurulacak (P27): `olcum` bugüne kadarki ölçüm öneği,"
        " `uretim` `turn/runner.py`'nin modele gerçekten gönderdiği dizi — rol metni,"
        " `[özet]` ve olgular dâhil. `bellek` kümesi her hâlükârda üretim öneğiyle koşar",
    )
    parser.add_argument(
        "--ornekleme",
        choices=["greedy", "sunucu"],
        default="greedy",
        help="Örnekleme ayarlarının kaynağı. `greedy` (varsayılan) `Sampling()`'in açgözlü"
        " ve cezasız kümesini gönderir — `docs/faz2-olcum.md`'den beri her sayı bu kabulle"
        " okundu, o yüzden varsayılan odur. `sunucu` ayarları `/props`'tan okur ve onları"
        " gönderir: kendi sıcaklığı/cezası için ayarlanmış bir modelde (LFM2.5) gereken bu."
        " Değerler sunucudan gelir, gönderim yine açık kalır — bir sunucu bayrağının sessizce"
        " karar vermesine kapatılan kapı yerinde duruyor. Rapor hangisiyle koştuğunu yazar",
    )
    parser.add_argument(
        "--bicim",
        action="append",
        choices=[f.value for f in CallFormat],
        help="Ölçülecek çağrı biçimi; birden çok kez verilebilir. Verilmezse **yalnızca"
        " üretimin biçimi** koşulur (`main.py:CALL_FORMAT`). Önceden üçü birden koşuluyordu;"
        " §19.1 kapandıktan sonra bu, her koşuyu iki ölü yol uğruna üç katına çıkarmak"
        " demekti. İki metin biçimi silinmedi — üretilmeye, ayrıştırılmaya ve test edilmeye"
        " devam ediyor, sadece istenmedikçe ölçülmüyor. Bir model değişiminde `--bicim cli"
        " --bicim json` ile geri gelirler",
    )
    args = parser.parse_args(argv)
    sets: list[str] = args.kume or ["altin"]
    formats = [CallFormat(v) for v in (args.bicim or [CALL_FORMAT.value])]
    chosen = [Prefix[name.upper()] for name in (args.onek or [Prefix.OLCUM.name.lower()])]

    config = load()
    # Defter yapılandırmadan kuruluyor, tıpkı `main.py`'de olduğu gibi: `app_launch`'ın
    # seçenekleri oradan geliyor ve yapılandırmasız kurulan bir defter, üretimin hiç
    # kullanmadığı bir katalog ölçerdi — P27'nin öneği için öğrendiği şeyin aynısı.
    registry = builtin_registry(config)
    # Rol metinleri yalnızca üretim öneğinde kullanılıyor ama **koşudan önce** okunuyor:
    # yolu yanlışsa hata, yirmi dakikalık bir ölçümün ortasında değil başında görünmeli.
    roles: list[tuple[Path | None, str | None]] = [(None, None)]
    if Prefix.URETIM in {*chosen, *(PREFIXES.get(name) for name in sets)}:
        paths: list[Path] = args.rol or ([config.role_path] if config.role_path else [])
        if not paths:
            print(
                "üretim öneği için rol metni gerekli: --rol ya da MAYEN_ROLE_PATH"
                " (§8.1: rolün kodda kopyası yok)",
                file=sys.stderr,
            )
            return 1
        try:
            roles = [(path, load_role(path)) for path in paths]
        except ConfigError as error:
            print(str(error), file=sys.stderr)
            return 1
    # Kuralsız kol daima ilk sırada: ölçülen şey kuralın **farkı**, kuralın kendisi değil.
    rules: list[tuple[str | None, str | None]] = [(None, None)]
    try:
        rules += [(path.stem, load_role(path)) for path in (args.dil_kurali or [])]
    except ConfigError as error:
        print(str(error), file=sys.stderr)
        return 1
    async with httpx.AsyncClient(base_url=config.llm_url, timeout=TIMEOUT_SECONDS) as http:
        llm = LlamaCppLLM(http, name=args.model)
        if not await llm.health():
            print(f"LLM servisi yanıt vermiyor: {config.llm_url}", file=sys.stderr)
            return 1
        # Sunucunun kendi bildirdiği ayarlar rapora giriyor (P25.3). Adaptöre değil
        # buraya konuldu: bir ölçüm aracının merakı, tur akışının ihtiyacı değil.
        props = (await http.get("/props")).json()
        if args.ornekleme == "sunucu":
            # Sunucunun bildirdiği ayarlarla yeniden kuruluyor. `Sampling` frozen, alanı
            # yerinde değiştirilemez; zaten kurulmuş istemciyi bırakıp yenisini kurmak
            # `health()`/`/props` çağrılarını da açgözlü kolla aynı sırada tutuyor.
            llm = LlamaCppLLM(http, name=args.model, sampling=await llm.server_sampling())

        runs = []
        for call_format in formats:
            for scenarios, tool_rows, prefix, suffix in _runs(sets, chosen):
                if call_format is CallFormat.YEREL and prefix is Prefix.OLCUM:
                    # Ölçüm öneği katalogu sistem mesajına yazıyor; yerel biçimde katalog
                    # `tools` alanından gidiyor ve ikisi birlikte defterin iki kopyası
                    # olurdu. Yerel biçim yalnızca üretim öneğiyle anlamlı.
                    continue
                for path, role in roles:
                    for rule_name, rule in rules:
                        # Rol adı yalnızca birden çok rol koşulduğunda etikete giriyor: tek
                        # rolde her satıra aynı eki yazmak, etiketi okunmaz uzatırdı.
                        tag = f" × rol({path.stem})" if path and len(roles) > 1 else ""
                        if len(rules) > 1:
                            tag += f" × dil({rule_name or 'yok'})"
                        label = (
                            f"{args.model} × {call_format.value}{suffix} × {prefix.value}{tag}"
                        )
                        print(f"koşuluyor: {label}", file=sys.stderr)
                        results = await run_all(
                            registry,
                            llm,
                            call_format,
                            scenarios,
                            tool_rows=tool_rows,
                            prefix=prefix,
                            role=role,
                            language_rule=rule,
                        )
                        runs.append((label, results))

    report = render(
        runs,
        server=props,
        sampling=llm.sampling,
        role_paths=[path for path, role in roles if path and role],
    )
    if args.out is None:
        print(report)
    else:
        args.out.write_text(report, encoding="utf-8")
        print(f"rapor yazıldı: {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""Altın kümenin kendi tutarlılığı.

Bu dosya modeli ölçmez; **altın kümeyi** ölçer. Bir tool'un imzası değiştiğinde senaryolar
sessizce yanlış beklentiye dönüşür ve ölçüm, kendi bozukluğunu modelin hatası diye
raporlar. Buradaki testler tam olarak bunu engeller.
"""

import json
from collections import Counter
from collections.abc import Sequence

import pytest
from evals.__main__ import _runs
from evals.runner import Prefix
from evals.scenarios import (
    APPROVAL_SCENARIOS,
    CONTROL_SCENARIOS,
    HALLUCINATION_SCENARIOS,
    HISTORY_SCENARIOS,
    LONG_HISTORY,
    LONG_RESULT_SCENARIOS,
    LONG_WINDOW,
    MEMORY_SCENARIOS,
    ROBUST_SCENARIOS,
    SCENARIOS,
    STEP2_SCENARIOS,
    Kind,
    Scenario,
)

from mayen.memory.recall import STALE_WARNING
from mayen.policy.effects import Effect
from mayen.tools.catalog import builtin_registry
from mayen.tools.registry import Registry
from mayen.tools.spec import ArgType, Tool


@pytest.fixture(scope="module")
def registry() -> Registry:
    return builtin_registry()


def test_there_are_fifty_scenarios() -> None:
    """§18: 50 Türkçe senaryo."""
    assert len(SCENARIOS) == 50


def test_every_axis_is_represented() -> None:
    """§18 altı zorluk ekseni sayıyor; biri boş kalırsa dağılım o ekseni ölçmüyor demektir."""
    counts = Counter(scenario.kind for scenario in SCENARIOS)
    assert set(counts) == set(Kind)
    assert min(counts.values()) >= 6


def test_ids_and_texts_are_unique() -> None:
    assert len({s.id for s in SCENARIOS}) == len(SCENARIOS)
    assert len({s.text for s in SCENARIOS}) == len(SCENARIOS)


@pytest.mark.parametrize("scenario", [*SCENARIOS, *HISTORY_SCENARIOS], ids=lambda s: s.id)
def test_expected_call_matches_a_real_signature(scenario: Scenario, registry: Registry) -> None:
    if scenario.expected is None:
        return
    assert scenario.expected.tool in registry
    tool: Tool = registry.get(scenario.expected.tool)
    known = {arg.name for arg in tool.args}
    assert set(scenario.expected.arguments) <= known
    required = {arg.name for arg in tool.args if arg.required}
    assert required <= set(scenario.expected.arguments)


@pytest.mark.parametrize("scenario", [*SCENARIOS, *HISTORY_SCENARIOS], ids=lambda s: s.id)
def test_exact_expectations_survive_validation(scenario: Scenario, registry: Registry) -> None:
    """Beklenen ham değerler tool'un kendi doğrulamasından geçmeli — geçmiyorsa altın
    küme, modelin asla üretemeyeceği bir cevabı doğru sayıyor demektir."""
    if scenario.expected is None:
        return
    raw = {
        name: value
        for name, value in scenario.expected.arguments.items()
        if isinstance(value, str)
    }
    tool = registry.get(scenario.expected.tool)
    missing = {arg.name for arg in tool.args if arg.required} - set(raw)
    if missing:
        return  # zorunlu alanı ANY olan senaryo; doğrulama tam yapılamaz
    tool.validate(raw)


def test_scenarios_without_a_call_are_only_where_prose_is_right() -> None:
    """Çağrı beklenmeyen tek iki eksen: hiç tool gerektirmeyen ve eksik argümanlı."""
    for scenario in SCENARIOS:
        if scenario.expected is None:
            assert scenario.kind in (Kind.TOOL_GEREKMEZ, Kind.EKSIK_ARGUMAN)
        else:
            assert scenario.kind is not Kind.TOOL_GEREKMEZ


def test_the_list_encoding_is_exercised(registry: Registry) -> None:
    """§8.3'ün `--fields a,b` kodlaması altın kümede sınanmalı; yoksa gerçek modelde hiç
    ölçülmemiş olur (P7'den P13'e kadar öyleydi)."""
    covered = [
        scenario
        for scenario in SCENARIOS
        if scenario.expected is not None
        and any(
            arg.type is ArgType.LIST and arg.name in scenario.expected.arguments
            for arg in registry.get(scenario.expected.tool).args
        )
    ]
    assert covered


def test_free_text_scenarios_target_a_trailing_field(registry: Registry) -> None:
    """§8.3'ün serbest metin alanı imzada en sonda duran alandır; bu eksen onu ölçmeli."""
    for scenario in SCENARIOS:
        if scenario.kind is not Kind.SERBEST_METIN:
            continue
        assert scenario.expected is not None
        tool = registry.get(scenario.expected.tool)
        assert any(arg.trailing for arg in tool.args)


# --- geçmişli küme --------------------------------------------------------------------


def test_the_golden_set_stays_history_free() -> None:
    """`docs/faz2-olcum.md` o 50 senaryoyla ölçüldü; birine geçmiş eklemek bütün önceki
    raporları sessizce karşılaştırılamaz kılardı."""
    assert all(not scenario.history for scenario in SCENARIOS)


def test_history_scenarios_have_history() -> None:
    assert HISTORY_SCENARIOS
    assert all(scenario.history for scenario in HISTORY_SCENARIOS)


def test_history_ids_and_texts_do_not_collide_with_the_golden_set() -> None:
    ids = {s.id for s in SCENARIOS} | {s.id for s in HISTORY_SCENARIOS}
    assert len(ids) == len(SCENARIOS) + len(HISTORY_SCENARIOS)


def test_both_context_buckets_are_populated() -> None:
    """Kısa ve uzun ayrı raporlanıyor; biri boşsa o kırılım hiçbir şey ölçmüyor demektir."""
    lengths = [len(s.history) for s in HISTORY_SCENARIOS]
    assert any(n < LONG_HISTORY for n in lengths)
    assert any(n >= LONG_HISTORY for n in lengths)


def test_over_calling_is_measured_too() -> None:
    """Tek yönlü ölçülen bir iyileşme, ölçülmemiş bir bozulmayı gizler: geçmişli kümede
    doğru davranışın düz metin olduğu senaryolar da olmalı."""
    assert any(s.expected is None for s in HISTORY_SCENARIOS)


def test_the_history_claims_are_toolless_where_the_trap_needs_it() -> None:
    """Tuzağın kendisi çağrısız iddia: `tool=None` olan geçmiş turlar olmadan bu küme
    yalnızca kolay senaryolardan oluşurdu."""
    assert any(past.tool is None for scenario in HISTORY_SCENARIOS for past in scenario.history)


# --- P25.2 kümeleri --------------------------------------------------------------------

ALL_SETS = (
    *SCENARIOS,
    *APPROVAL_SCENARIOS,
    *HALLUCINATION_SCENARIOS,
    *MEMORY_SCENARIOS,
    *HISTORY_SCENARIOS,
    *CONTROL_SCENARIOS,
    *STEP2_SCENARIOS,
    *ROBUST_SCENARIOS,
    *LONG_RESULT_SCENARIOS,
)


def test_ids_are_unique_across_every_set() -> None:
    """Raporun satır anahtarı `id`; iki küme aynı id'yi kullanırsa iki farklı senaryonun
    sonucu tek satırmış gibi okunur."""
    assert len({s.id for s in ALL_SETS}) == len(ALL_SETS)


@pytest.mark.parametrize(
    "scenarios",
    [
        SCENARIOS,
        CONTROL_SCENARIOS,
        STEP2_SCENARIOS,
        ROBUST_SCENARIOS,
        LONG_RESULT_SCENARIOS,
        HALLUCINATION_SCENARIOS,
        MEMORY_SCENARIOS,
        APPROVAL_SCENARIOS,
    ],
    ids=[
        "altin",
        "kontrol",
        "adim2",
        "saglamlik",
        "uzun",
        "halusinasyon",
        "bellek",
        "onay",
    ],
)
def test_texts_are_unique_within_a_set(scenarios: Sequence[Scenario]) -> None:
    """Aynı metin bir kümede iki kere geçerse aynı senaryo iki kere ölçülmüş demektir.

    **`HISTORY_SCENARIOS` bu kuralın dışında, bilerek:** `gec-06` `gec-03`'ün cümlesini
    aynen tekrar ediyor ve `gec-09` da `tek-03`'ünkine yakın duruyor — o kümede ölçülen
    şey cümlenin kendisi değil, aynı cümlenin farklı uzunluktaki geçmişle karşılaşması.
    Cümle değişirse karşılaştırma iki farklı sınavın karşılaştırması olur.
    """
    assert len({s.text for s in scenarios}) == len(scenarios)


@pytest.mark.parametrize("scenario", ALL_SETS, ids=lambda s: s.id)
def test_every_expected_call_in_every_set_matches_a_signature(
    scenario: Scenario, registry: Registry
) -> None:
    for expected in (scenario.expected, scenario.step2.expected if scenario.step2 else None):
        if expected is None:
            continue
        assert expected.tool in registry
        tool: Tool = registry.get(expected.tool)
        known = {arg.name for arg in tool.args}
        assert set(expected.arguments) <= known
        required = {arg.name for arg in tool.args if arg.required}
        assert required <= set(expected.arguments)


def test_the_control_set_is_entirely_negative() -> None:
    """Kümenin varlık sebebi fazla çağrıyı ölçmek; bir satırında bile çağrı beklenirse
    o satır bu soruyu değil, başka bir soruyu ölçer."""
    assert len(CONTROL_SCENARIOS) >= 18
    assert all(s.expected is None for s in CONTROL_SCENARIOS)
    assert all(s.kind is Kind.TOOL_GEREKMEZ for s in CONTROL_SCENARIOS)


def test_the_control_set_contains_keyword_traps() -> None:
    """Anahtar kelime içerip istek olmayan cümleler olmadan küme yalnızca kolay
    senaryolardan oluşurdu — bir anahtar kelime eşleştiricisi de %100 alırdı."""
    traps = ("hava", "Ali", "Saatin", "ders")
    for word in traps:
        assert any(word in s.text for s in CONTROL_SCENARIOS)


def test_step2_scenarios_carry_a_result() -> None:
    """Geri beslenecek sonuç yoksa ikinci adım diye bir şey de yok."""
    assert all(s.result is not None for s in STEP2_SCENARIOS)
    assert all(s.step2 is not None for s in STEP2_SCENARIOS)


def test_step2_has_negative_controls_and_a_follow_up_question() -> None:
    assert any(s.step2 is not None and s.step2.expected is None for s in STEP2_SCENARIOS)
    assert any(s.step2 is not None and s.step2.user is not None for s in STEP2_SCENARIOS)


def test_only_step2_scenarios_define_step2() -> None:
    """`step2` yanıt turuyla birbirini dışlar; başka bir kümeye sızması, o kümenin
    desteksiz sayı sayacını sessizce kapatırdı."""
    for scenario in ALL_SETS:
        if scenario.step2 is not None:
            assert scenario in STEP2_SCENARIOS
            assert scenario.result is not None


def test_the_robust_set_exercises_both_grammar_bans() -> None:
    """A4'ün `--` ve P11'in `<` yasağı; ikisinin de model tarafı bugüne kadar ölçülmedi."""
    assert any("--" in s.text for s in ROBUST_SCENARIOS)
    assert any("<" in s.text for s in ROBUST_SCENARIOS)


def test_long_results_are_actually_long() -> None:
    """ "Uzun sonuç" kümesi kısa sonuçlarla dolarsa, ölçtüğü şey altın kümenin aynısı olur.
    Eşik karakter cinsinden ve gevşek: token sayacı burada koşmuyor (Kural 10 sunucuya
    sorulmasını istiyor, ve bu bir senaryo tutarlılık testi, ölçüm değil)."""
    assert LONG_RESULT_SCENARIOS
    for scenario in LONG_RESULT_SCENARIOS:
        assert scenario.result is not None
        assert len(json.dumps(scenario.result, ensure_ascii=False)) > 4000


# --- eylem halüsinasyonu kümesi (P26) --------------------------------------------------


def test_the_hallucination_set_is_big_enough() -> None:
    """P26: en az 12 senaryo. Daha azı, tek bir kötü cümlenin oranı sürüklemesi demek."""
    assert len(HALLUCINATION_SCENARIOS) >= 12


def test_every_trap_carries_a_toolless_claim() -> None:
    """Tuzağın kendisi bu: geçmişte çağrısız duran bir "tamam, yaptım" cümlesi. Negatif
    kontrol satırları hariç her senaryoda bulunmalı; yoksa küme başka bir şey ölçüyordur."""
    traps = [s for s in HALLUCINATION_SCENARIOS if s.id not in ("hal-13", "hal-14", "hal-15")]
    assert traps
    for scenario in traps:
        assert any(past.tool is None for past in scenario.history)


def test_the_expected_answer_is_always_a_reading_call() -> None:
    """Ölçülen şey "iddiayı doğrulamadan onaylamamak": doğru davranış okumak. Bir yazma
    tool'u beklenirse o satır bu soruyu değil, `gec-04`'ün hatasını doğru sayardı."""
    reading = {"note_search", "task_list", "contact_get", "fact_list", "course_schedule"}
    for scenario in HALLUCINATION_SCENARIOS:
        if scenario.expected is not None:
            assert scenario.expected.tool in reading


def test_the_set_has_a_verified_history_control() -> None:
    """Negatif kontrol: geçmişte tool **gerçekten** çağrılmış. Onlar olmadan küme,
    "izi olmayan her cümleye bir okuma çağrısı" eğilimini iyileşme diye raporlardı."""
    assert any(
        any(past.tool is not None for past in s.history) for s in HALLUCINATION_SCENARIOS
    )


def test_the_set_has_a_prose_control() -> None:
    """Aynı gerekçenin diğer ucu: her cümleye çağrı yazmak da bir hata."""
    assert any(s.expected is None for s in HALLUCINATION_SCENARIOS)


def test_both_context_buckets_are_populated_in_the_hallucination_set() -> None:
    """Aynı tuzak kısa ve uzun geçmişte ayrı raporlanıyor; biri boşsa kırılım boş."""
    lengths = [len(s.history) for s in HALLUCINATION_SCENARIOS]
    assert any(n < LONG_HISTORY for n in lengths)
    assert any(n >= LONG_HISTORY for n in lengths)


# --- bellek kümesi (P27) ---------------------------------------------------------------


def test_the_memory_set_is_big_enough() -> None:
    """P27: en az 15 senaryo, beş şekle bölünmüş."""
    assert len(MEMORY_SCENARIOS) >= 15


def test_every_memory_scenario_carries_a_summary_or_facts() -> None:
    """Kümenin varlık sebebi bu iki blok; ikisini de taşımayan satır başka bir şey ölçer."""
    for scenario in MEMORY_SCENARIOS:
        assert scenario.summary is not None or scenario.facts is not None


def test_the_stale_warning_is_the_production_text() -> None:
    """Uyarı `memory/recall.py`'den geliyor; ikinci bir kopya yazılsaydı uyarı
    değiştiğinde ölçüm eskisini ölçmeye devam ederdi."""
    stale = [s for s in MEMORY_SCENARIOS if s.facts is not None]
    assert stale
    for scenario in stale:
        assert scenario.facts is not None
        assert STALE_WARNING in scenario.facts


def test_the_long_window_is_actually_long() -> None:
    """ "Uzun pencere" kovası kısa geçmişle dolarsa, ölçtüğü şey `gecmis` kümesinin aynısı."""
    assert LONG_WINDOW >= 20
    assert any(len(s.history) >= LONG_WINDOW for s in MEMORY_SCENARIOS)


def test_the_memory_set_has_a_negative_control_with_two_right_answers() -> None:
    """Bilgi hiçbir yerde yoksa hem 'bilmiyorum' hem okuma çağrısı doğrudur; birini
    seçip diğerini hata saymak modelin doğrusunu yanlış raporlamak olurdu."""
    controls = [s for s in MEMORY_SCENARIOS if s.accepted]
    assert controls
    for scenario in controls:
        assert None in scenario.accepted


def test_no_other_set_uses_accepted_alternatives() -> None:
    """Alternatifler yeni bir alan; eski kümelerde kullanılmadığı sürece hiçbir eski sayı
    kıpırdamaz (P27'nin bitti kriteri)."""
    for scenario in ALL_SETS:
        if scenario not in MEMORY_SCENARIOS:
            assert not scenario.accepted


# --- onay kümesi (2026-08-15) ----------------------------------------------------------


def test_the_approval_set_measures_both_directions() -> None:
    """İzin verilen turda çağrı beklenir, reddedilen turda beklenmez. Tek yön ölçülürse
    "her onaydan sonra çağır" eğilimi iyileşme diye raporlanırdı (gec-05/10'un kuralı)."""
    assert any(s.expected is not None for s in APPROVAL_SCENARIOS)
    assert any(s.expected is None for s in APPROVAL_SCENARIOS)


def test_the_approval_questions_are_toolless_history() -> None:
    """Tuzağın şekli `bel-11`'in kendisi: modelin izin sorusu geçmişte **çağrısız**
    duruyor. İz eklenirse senaryo başka bir şey ölçer."""
    asked = [s for s in APPROVAL_SCENARIOS if s.history]
    assert asked
    for scenario in asked:
        assert all(past.tool is None for past in scenario.history)


def test_the_approval_set_covers_irreversible_tools(registry: Registry) -> None:
    """Onay akışı en çok geri alınamaz işlerde önemli; küme oraya değmezse ölçtüğü şey
    yalnızca kolay yarısı olur."""
    tools = {s.expected.tool for s in APPROVAL_SCENARIOS if s.expected is not None}
    assert any(registry.get(name).effect is Effect.GERI_ALINAMAZ for name in tools)


def test_a_forced_prefix_set_runs_exactly_once_whatever_the_flag() -> None:
    """Öneği sabit küme (`onay`, `bellek`) hangi `--onek` verilirse verilsin bir kez
    koşmalı.

    2026-08-15: seçilen önek `olcum` iken bu kümeler sessizce atlanıyordu ve rapor **boş**
    yazılıyordu — hiçbir hata çıkmadan. Kural 13'ün ruhu: sessizce hiçbir şey yapmamak da
    yutulmuş bir hatadır.
    """
    for chosen in ([Prefix.OLCUM], [Prefix.URETIM], [Prefix.OLCUM, Prefix.URETIM]):
        runs = _runs(["onay"], chosen)
        assert len(runs) == 1
        assert runs[0][2] is Prefix.URETIM


def test_a_free_set_runs_once_per_chosen_prefix() -> None:
    """Öneği sabit olmayan küme her önek için bir kez: iki kolonun kaynağı bu."""
    assert len(_runs(["altin"], [Prefix.OLCUM])) == 1
    assert len(_runs(["altin"], [Prefix.OLCUM, Prefix.URETIM])) == 2

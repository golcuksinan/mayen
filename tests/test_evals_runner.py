"""Koşucunun kendisi doğru sayıyor mu — sahte LLM ile, saniyeler içinde.

Ölçüm aracının hatası, modelin hatası gibi görünür ve raporlanır. Bu yüzden koşucu da
tıpkı ölçtüğü şey kadar test edilir.
"""

from collections.abc import AsyncGenerator
from dataclasses import replace
from pathlib import Path

import pytest
from evals.report import GRAMMAR_BOUND_COUNTERS, render, summarize, wilson
from evals.runner import (
    LONG_CONTEXT_TOKENS,
    Context,
    Prefix,
    ScenarioResult,
    called_line,
    context_of,
    history_messages,
    prefix_messages,
    run_all,
    run_scenario,
    system_prompt,
    user_prompt,
)
from evals.scenarios import (
    ANY,
    NOW,
    ExpectedCall,
    HistoryTurn,
    Kind,
    Scenario,
    Step2,
)

from mayen.adapters.errors import ServiceUnavailableError
from mayen.adapters.fakes.llm import FakeLLM
from mayen.adapters.llm import PromptMessage
from mayen.agent.calls import CallFormat
from mayen.agent.prompt import ContextBlock, build_messages
from mayen.agent.prompt import system_prompt as agent_system_prompt
from mayen.tools.catalog import builtin_registry
from mayen.tools.grammar import CALL_PREFIX
from mayen.tools.registry import Registry


@pytest.fixture
def registry() -> Registry:
    return builtin_registry()


def _scenario(
    expected: ExpectedCall | None = None, kind: Kind = Kind.TEK_TOOL, text: str = "deneme"
) -> Scenario:
    return Scenario("t-01", kind, text, expected)


def test_system_prompt_carries_the_syntax_and_the_catalog(registry: Registry) -> None:
    text = system_prompt(registry, CallFormat.CLI)
    assert CALL_PREFIX in text
    assert "weather" in text


def test_variable_content_sits_at_the_end_of_the_prefix(registry: Registry) -> None:
    """§8.1: sabit önek senaryodan senaryoya değişmez, tarih/saat kullanıcı turunda."""
    first = system_prompt(registry, CallFormat.CLI)
    second = system_prompt(registry, CallFormat.CLI)
    assert first == second
    assert NOW not in first
    assert NOW in user_prompt(_scenario(text="Saat kaç?"))


async def test_correct_call_is_graded_correct(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli"])
    result = await run_scenario(
        registry,
        llm,
        CallFormat.CLI,
        _scenario(ExpectedCall("weather", {"city": "Denizli"})),
    )
    assert result.tool_correct
    assert result.arguments_correct
    assert result.corrections == 0
    assert result.failures == ()


async def test_wrong_tool_leaves_argument_accuracy_undefined(registry: Registry) -> None:
    """Yanlış tool'un argümanını doğru ya da yanlış saymak, ikisi de anlamsız."""
    llm = FakeLLM([f"{CALL_PREFIX}system_metrics"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("weather", {"city": "Denizli"}))
    )
    assert not result.tool_correct
    assert result.arguments_correct is None


async def test_argument_comparison_is_exact(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}weather --city denizli"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("weather", {"city": "Denizli"}))
    )
    assert result.tool_correct
    assert result.arguments_correct is False


async def test_trailing_sentence_punctuation_is_not_a_mistake(registry: Registry) -> None:
    """Kullanıcının cümlesini bitiren nokta argümanın içeriği değil."""
    llm = FakeLLM([f"{CALL_PREFIX}note_create --body süt al."])
    result = await run_scenario(
        registry,
        llm,
        CallFormat.CLI,
        _scenario(ExpectedCall("note_create", {"body": "süt al"})),
    )
    assert result.arguments_correct


async def test_case_is_still_compared(registry: Registry) -> None:
    """Noktalama atılıyor, harf katlaması yapılmıyor: Türkçe'de `I`/`ı` üzerinde yanlıştır."""
    llm = FakeLLM([f"{CALL_PREFIX}weather --city denizli"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("weather", {"city": "Denizli"}))
    )
    assert result.arguments_correct is False


async def test_any_checks_presence_not_value(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}note_search --query her neyse"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("note_search", {"query": ANY}))
    )
    assert result.arguments_correct


async def test_missing_and_extra_arguments_are_both_wrong(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}contact_save --name Ali --phone 555"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("contact_save", {"name": "Ali"}))
    )
    assert result.arguments_correct is False
    assert any("phone" in failure for failure in result.failures)


async def test_prose_is_correct_when_no_call_is_expected(registry: Registry) -> None:
    llm = FakeLLM(["Rica ederim!"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(None, kind=Kind.TOOL_GEREKMEZ)
    )
    assert result.tool_correct
    assert result.call is None
    assert result.arguments_correct is None


async def test_a_call_where_prose_was_expected_is_wrong(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}date_time"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(None, kind=Kind.EKSIK_ARGUMAN)
    )
    assert not result.tool_correct


async def test_invalid_arguments_trigger_a_correction_round(registry: Registry) -> None:
    """§8.3: hatalı çağrıda kullanım metni modele geri beslenir; tur sayılır."""
    llm = FakeLLM([f"{CALL_PREFIX}note_delete --id üç", f"{CALL_PREFIX}note_delete --id 3"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("note_delete", {"id": "3"}))
    )
    assert result.corrections == 1
    assert result.tool_correct
    assert result.arguments_correct
    fed_back = llm.calls[-1][-1].content
    assert "note_delete" in fed_back


async def test_corrections_stop_at_the_ceiling(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}note_delete --id üç"] * 5)
    result = await run_scenario(
        registry,
        llm,
        CallFormat.CLI,
        _scenario(ExpectedCall("note_delete", {"id": "3"})),
        max_corrections=2,
    )
    assert result.corrections == 2
    assert result.call is None
    assert not result.tool_correct


async def test_hallucination_counters_are_separate(registry: Registry) -> None:
    llm = FakeLLM(
        [
            f"{CALL_PREFIX}send_email --to Ali",
            f"{CALL_PREFIX}weather --city Denizli --units metric",
            f"{CALL_PREFIX}weather --city Denizli",
        ]
    )
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("weather", {"city": "Denizli"}))
    )
    assert result.unknown_tool == 1
    assert result.unknown_argument == 1
    assert result.corrections == 2
    assert result.tool_correct


async def test_tokens_come_from_the_counter(registry: Registry) -> None:
    """Kural 10: üretilen token sayısı da sayaçtan gelir, uzunluktan tahmin edilmez."""
    llm = FakeLLM(["bir iki üç"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(None, kind=Kind.TOOL_GEREKMEZ)
    )
    assert result.tokens == 3


async def test_json_format_is_graded_the_same_way(registry: Registry) -> None:
    payload = '{"name": "weather", "arguments": {"city": "Denizli"}}'
    llm = FakeLLM([CALL_PREFIX + payload])
    result = await run_scenario(
        registry,
        llm,
        CallFormat.JSON,
        _scenario(ExpectedCall("weather", {"city": "Denizli"})),
    )
    assert result.tool_correct
    assert result.arguments_correct
    assert llm.grammars[-1] is not None


async def test_summary_keeps_the_counters_apart(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli", "Rica ederim!"])
    first = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("weather", {"city": "Denizli"}))
    )
    second = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(None, kind=Kind.TOOL_GEREKMEZ)
    )
    summary = summarize("deneme", [first, second])
    assert summary.count == 2
    assert summary.tool_accuracy == 1.0
    assert summary.argument_accuracy == 1.0


async def test_summary_leaves_argument_accuracy_undefined_without_a_graded_call(
    registry: Registry,
) -> None:
    llm = FakeLLM(["Rica ederim!"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(None, kind=Kind.TOOL_GEREKMEZ)
    )
    assert summarize("deneme", [result]).argument_accuracy is None


async def test_report_names_the_scope_of_the_third_counter(registry: Registry) -> None:
    """Kural 14: sayaç dar adıyla ve paydasıyla yazılıyor."""
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("weather", {"city": "Denizli"}))
    )
    text = render([("deneme", [result])])
    assert "desteksiz sayı" in text
    assert "Eksen kırılımı" in text


# --- §17.1'in üçüncü sayacı ------------------------------------------------------------


def _weather_scenario(result: dict[str, object] | None) -> Scenario:
    return Scenario(
        "t-01",
        Kind.TEK_TOOL,
        "Denizli'de hava nasıl?",
        ExpectedCall("weather", {"city": "Denizli"}),
        result=result,
    )


async def test_no_answer_round_without_a_canned_result(registry: Registry) -> None:
    """Hazır sonucu olmayan senaryo sayacın paydasına girmez."""
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli"])
    result = await run_scenario(registry, llm, CallFormat.CLI, _weather_scenario(None))
    assert result.answer is None
    assert result.unsupported_numbers == ()
    assert summarize("deneme", [result]).answered == 0


async def test_numbers_from_the_tool_result_are_supported(registry: Registry) -> None:
    llm = FakeLLM(
        [f"{CALL_PREFIX}weather --city Denizli", "Denizli'de hava 31 derece ve açık."]
    )
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _weather_scenario({"temperature": 31, "humidity": 24})
    )
    assert result.answer is not None
    assert result.unsupported_numbers == ()
    assert summarize("deneme", [result]).answered == 1


async def test_a_number_absent_from_the_result_is_counted(registry: Registry) -> None:
    """§17.1'in üçüncüsü: sonuçta nem var, rüzgâr yok — 12 desteksizdir."""
    llm = FakeLLM(
        [
            f"{CALL_PREFIX}weather --city Denizli",
            "Denizli'de 31 derece, nem 24 ve rüzgâr 12 km/s.",
        ]
    )
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _weather_scenario({"temperature": 31, "humidity": 24})
    )
    assert result.unsupported_numbers == ("12",)
    assert summarize("deneme", [result]).unsupported_numbers == 1


async def test_the_decimal_separator_is_not_a_claim(registry: Registry) -> None:
    """`9,4` ile `9.4` aynı sayı; ayracı hata saymak modelin doğrusunu yanlış raporlardı."""
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli", "Bellek 9,4 GB kullanılıyor."])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _weather_scenario({"memory_used_gb": 9.4})
    )
    assert result.unsupported_numbers == ()


async def test_the_answer_round_cannot_produce_a_tool_call(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli", "31 derece."])
    await run_scenario(registry, llm, CallFormat.CLI, _weather_scenario({"temperature": 31}))
    assert "tool-call" not in (llm.grammars[-1] or "")


async def test_unsupported_numbers_are_listed_in_the_report(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli", "Rüzgâr 12 km/s."])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _weather_scenario({"temperature": 31})
    )
    assert "`12`" in render([("deneme", [result])])


# --- geçmişli senaryolar --------------------------------------------------------------


def _with_history(*turns: HistoryTurn) -> Scenario:
    return Scenario("g-01", Kind.TEK_TOOL, "hava nasıl", history=turns)


def test_history_is_rendered_the_way_the_turn_stores_it() -> None:
    """Ölçümün geçmişi üretimin geçmişine benzemezse, ölçülen şey üretim olmaz."""
    scenario = _with_history(HistoryTurn("hava nasıl", "On sekiz derece.", tool="weather"))
    assert [(m.role, m.content) for m in history_messages(scenario)] == [
        ("user", "hava nasıl"),
        ("tool", called_line(["weather"])),
        ("assistant", "On sekiz derece."),
    ]


def test_tool_rows_can_be_left_out_to_rebuild_the_old_history() -> None:
    """2026-08-13 öncesi: iz satırı yoktu ve geçmiş, çağrısız cevabın örneğiydi."""
    scenario = _with_history(HistoryTurn("hatırlat", "Tamam, kurdum.", tool="task_create"))
    roles = [m.role for m in history_messages(scenario, tool_rows=False)]
    assert roles == ["user", "assistant"]


def test_a_turn_that_called_nothing_has_no_trace_either() -> None:
    scenario = _with_history(HistoryTurn("hatırlat", "Tamam, kurdum."))
    assert [m.role for m in history_messages(scenario)] == ["user", "assistant"]


async def test_history_reaches_the_model_before_the_user_turn(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli"])
    scenario = _with_history(HistoryTurn("selam", "Merhaba."))
    await run_scenario(registry, llm, CallFormat.CLI, scenario)
    roles = [message.role for message in llm.calls[0]]
    assert roles == ["system", "user", "assistant", "user"]
    assert llm.calls[0][-1].content.endswith(scenario.text)


def test_context_buckets_split_short_from_long() -> None:
    """Kova sınırı bir rapor ayrımı; ölçüm kısa ve uzun geçmişi karıştırmamalı.

    Sınır artık jeton (P27): tur sayısı "uzun"u 247 karakterlik bir blok diye
    tanımlıyordu ve modele giden şey tur değil jeton.
    """
    with_history = _with_history(HistoryTurn("a", "b"))
    assert context_of(_scenario(), LONG_CONTEXT_TOKENS * 10) is Context.YOK
    assert context_of(with_history, LONG_CONTEXT_TOKENS - 1) is Context.KISA
    assert context_of(with_history, LONG_CONTEXT_TOKENS) is Context.UZUN


async def test_the_context_bucket_is_measured_not_estimated(registry: Registry) -> None:
    """Kural 10: jeton sayısı sunucudan sorulur. Sabit önek dışarıda — her senaryoda aynı
    ve hiçbir kovayı diğerinden ayırmıyor."""
    llm = FakeLLM([f"{CALL_PREFIX}date_time"])
    scenario = _with_history(HistoryTurn("selam", "Merhaba."))
    result = await run_scenario(registry, llm, CallFormat.CLI, scenario)
    assert result.context_tokens > 0
    assert result.context_tokens < await llm.count_tokens(
        "\n".join(m.content for m in llm.calls[0])
    )


async def test_the_report_splits_the_context_buckets(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli"])
    result = await run_scenario(
        registry,
        llm,
        CallFormat.CLI,
        Scenario(
            "g-02",
            Kind.TEK_TOOL,
            "hava nasıl",
            ExpectedCall("weather", {"city": "Denizli"}),
            history=(HistoryTurn("selam", "Merhaba."),),
        ),
    )
    text = render([("deneme", [result])])
    assert "Bağlam kırılımı" in text
    assert Context.KISA.value in text


def test_the_context_section_stays_out_of_a_history_free_report(registry: Registry) -> None:
    """Altın kümenin raporu değişmemeli: boş bir kova tablosu okuyanı yanıltırdı."""
    result = ScenarioResult(
        scenario_id="t-01",
        kind=Kind.TEK_TOOL,
        context=Context.YOK,
        call_format=CallFormat.CLI,
        model="sahte",
        output="",
        call=None,
        tool_correct=True,
        arguments_correct=None,
        unknown_tool=0,
        unknown_argument=0,
        corrections=0,
        tokens=0,
        seconds=0.0,
    )
    assert "Bağlam kırılımı" not in render([("deneme", [result])])


# --- ikinci adım (P25.2) ----------------------------------------------------------------


def _chain(step2: Step2) -> Scenario:
    return Scenario(
        "t-02",
        Kind.COK_TOOL,
        "Veli'nin numarasını bul, sonra not al.",
        ExpectedCall("contact_get", {"name": "Veli"}),
        result={"name": "Veli", "phone": "0532 111 22 33"},
        step2=step2,
    )


async def test_second_step_is_graded(registry: Registry) -> None:
    llm = FakeLLM(
        [
            f"{CALL_PREFIX}contact_get --name Veli",
            f"{CALL_PREFIX}note_create --body Veli'yi akşam ara",
        ]
    )
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _chain(Step2(ExpectedCall("note_create", {"body": ANY})))
    )
    assert result.tool_correct
    assert result.step2_run
    assert result.step2_tool_correct
    assert result.step2_arguments_correct
    assert result.step2_call is not None
    assert result.step2_call.name == "note_create"


async def test_a_wrong_second_step_says_which_step_failed(registry: Registry) -> None:
    """İki adımın hatası raporda aynı satırda duruyor; hangisi olduğu yazılmazsa okunamaz."""
    llm = FakeLLM(
        [f"{CALL_PREFIX}contact_get --name Veli", f"{CALL_PREFIX}weather --city Denizli"]
    )
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _chain(Step2(ExpectedCall("note_create", {"body": ANY})))
    )
    assert result.tool_correct
    assert result.step2_tool_correct is False
    assert any("2. adım" in failure for failure in result.failures)


async def test_an_extra_second_call_is_a_failure(registry: Registry) -> None:
    """Negatif kontrol: sonuç geldi, ikinci çağrı fazladan. Bu satırlar olmadan küme
    'her sonuçtan sonra bir çağrı daha' eğilimini iyileşme diye raporlardı."""
    llm = FakeLLM(
        [f"{CALL_PREFIX}contact_get --name Veli", f"{CALL_PREFIX}contact_get --name Veli"]
    )
    result = await run_scenario(registry, llm, CallFormat.CLI, _chain(Step2(None)))
    assert result.step2_tool_correct is False


async def test_prose_after_the_result_satisfies_a_negative_second_step(
    registry: Registry,
) -> None:
    llm = FakeLLM(
        [f"{CALL_PREFIX}contact_get --name Veli", "Veli'nin numarası 0532 111 22 33."]
    )
    result = await run_scenario(registry, llm, CallFormat.CLI, _chain(Step2(None)))
    assert result.step2_tool_correct
    assert result.step2_call is None


async def test_the_follow_up_question_reaches_the_model(registry: Registry) -> None:
    """`gec-04`'ün hatası: doğrulama sorusuna yeni bir çağrı. Soru öneğe girmezse bu
    senaryo hiçbir şey ölçmez."""
    llm = FakeLLM([f"{CALL_PREFIX}contact_get --name Veli", f"{CALL_PREFIX}task_list"])
    scenario = _chain(Step2(ExpectedCall("task_list"), user="Emin misin?"))
    result = await run_scenario(registry, llm, CallFormat.CLI, scenario)
    assert result.step2_tool_correct
    assert any("Emin misin?" in message.content for message in llm.calls[-1])


async def test_step2_and_the_answer_turn_exclude_each_other(registry: Registry) -> None:
    """İkisi iki farklı gramerle üretiliyor; aynı satıra ikisini birden yazmak, ölçülen
    şeyin ne olduğunu belirsiz bırakırdı."""
    llm = FakeLLM([f"{CALL_PREFIX}contact_get --name Veli", f"{CALL_PREFIX}task_list"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _chain(Step2(ExpectedCall("task_list")))
    )
    assert result.answer is None
    assert result.unsupported_numbers == ()


# --- güven aralığı (P25.2) --------------------------------------------------------------


def test_a_perfect_score_still_has_an_interval() -> None:
    """Normal yaklaşım burada `[100, 100]` derdi ve %100'ü kesinlik gibi okuturdu."""
    low, high = wilson(50, 50)
    assert high == 1.0
    assert 0.90 < low < 1.0


def test_the_interval_narrows_as_the_sample_grows() -> None:
    narrow = wilson(470, 500)
    wide = wilson(47, 50)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_p7s_two_numbers_overlap_at_fifty() -> None:
    """P7'nin "CLI 94, JSON 92" farkı n=50'de gürültünün içinde: aralık sütununun varlık
    sebebi tam olarak bu satırın gösterdiği şey."""
    cli = wilson(47, 50)
    json_ = wilson(46, 50)
    assert cli[0] < json_[1] and json_[0] < cli[1]


def test_an_empty_denominator_has_no_interval() -> None:
    with pytest.raises(ValueError):
        wilson(0, 0)


def _result() -> ScenarioResult:
    """Rapor testleri için asgari sonuç: sayıların hiçbiri ölçülmüyor, yalnızca metnin
    hangi bölümleri yazılıyor sınanıyor."""
    return ScenarioResult(
        scenario_id="t-01",
        kind=Kind.TEK_TOOL,
        context=Context.YOK,
        call_format=CallFormat.CLI,
        model="sahte",
        output="",
        call=None,
        tool_correct=True,
        arguments_correct=None,
        unknown_tool=0,
        unknown_argument=0,
        corrections=0,
        tokens=0,
        seconds=0.0,
    )


# --- TTFT ve sunucu ayarları (P25.3) ----------------------------------------------------


async def test_ttft_is_measured_and_is_not_the_completion_time(registry: Registry) -> None:
    """§6'nın bütçesi ilk ses; tamamlanma süresi üretilen token sayısıyla büyür, ilk ses
    büyümez. İkisi aynı sayıysa TTFT diye bir şey ölçülmemiş demektir."""
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("weather", {"city": "Denizli"}))
    )
    assert result.ttft > 0.0
    assert result.ttft <= result.seconds


async def test_ttft_ignores_correction_rounds(registry: Registry) -> None:
    """Düzeltme turu, kullanıcının ilk sesi beklediği yerde değil — zaten kaybedilmiş bir
    turun içinde. TTFT'ye katılırsa ölçülen şey §6'nın bütçesi olmaktan çıkar."""
    llm = FakeLLM([f"{CALL_PREFIX}weather --city", f"{CALL_PREFIX}weather --city Denizli"])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("weather", {"city": "Denizli"}))
    )
    assert result.corrections == 1
    assert result.ttft > 0.0


def test_the_server_block_is_omitted_when_nothing_was_read() -> None:
    """Boş bir ayar tablosu, ayarların ölçülmüş ama önemsiz olduğu izlenimi verirdi."""
    assert "Sunucu ayarları" not in render([("x", [_result()])])


def test_the_server_block_records_what_the_server_reported() -> None:
    props = {
        "model_path": "/models/Qwen3.6-27B.gguf",
        "model_ftype": "IQ4_XS",
        "default_generation_settings": {"n_ctx": 16384, "params": {"presence_penalty": 1.5}},
    }
    text = render([("x", [_result()])], server=props)
    assert "/models/Qwen3.6-27B.gguf" in text
    assert "16384" in text
    assert "`presence_penalty`=1.5" in text


# --- servis hatası koşuyu bitirmemeli (P25.3) -------------------------------------------


class _BrokenLLM(FakeLLM):
    """İlk `fail` üretimde kopar, sonra normale döner. 35B'nin koşusunu 26. üretimde
    öldüren `akış kesildi`in sahtesi."""

    def __init__(self, outputs: list[str], *, fail: int) -> None:
        super().__init__(outputs)
        self._fail = fail

    async def stream(self, *args: object, **kwargs: object) -> AsyncGenerator[str]:
        if self._fail > 0:
            self._fail -= 1
            raise ServiceUnavailableError("sahte", "akış kesildi: ")
        async for chunk in super().stream(*args, **kwargs):  # type: ignore[arg-type]
            yield chunk


async def test_one_dropped_stream_does_not_kill_the_run(registry: Registry) -> None:
    """25 dakikalık bir ölçüm tek bir kopan bağlantıyla çöpe gitmemeli. Senaryo baştan
    tekrar deneniyor — P12'nin yasağı yarısı tüketilmiş bir *akışı* tekrar oynatmak, bu
    değil."""
    llm = _BrokenLLM([f"{CALL_PREFIX}weather --city Denizli"] * 4, fail=1)
    results = await run_all(
        registry,
        llm,
        CallFormat.CLI,
        [_scenario(ExpectedCall("weather", {"city": "Denizli"}))],
    )
    assert len(results) == 1
    assert results[0].error is None
    assert results[0].tool_correct


async def test_a_scenario_that_fails_twice_is_recorded_not_dropped(
    registry: Registry,
) -> None:
    """Kural 13: sessizce atlanan senaryo, paydayı sessizce küçültür."""
    llm = _BrokenLLM([f"{CALL_PREFIX}weather --city Denizli"], fail=2)
    results = await run_all(
        registry,
        llm,
        CallFormat.CLI,
        [_scenario(ExpectedCall("weather", {"city": "Denizli"}))],
    )
    assert len(results) == 1
    assert results[0].error is not None
    assert "akış kesildi" in results[0].error


def test_unmeasured_scenarios_stay_out_of_every_denominator() -> None:
    """Ölçülemeyen senaryoyu yanlış saymak, modeli servisin kopmasından sorumlu tutmaktır."""
    good = _result()
    broken = replace(_result(), scenario_id="t-02", tool_correct=False, error="akış kesildi")
    summary = summarize("x", [good, broken])
    assert summary.count == 1
    assert summary.errors == 1
    assert summary.tool_accuracy == 1.0


def test_the_report_says_a_run_was_incomplete() -> None:
    broken = replace(_result(), tool_correct=False, error="akış kesildi: ")
    text = render([("x", [_result(), broken])])
    assert "Ölçülemeyen senaryolar" in text
    assert "eksiktir" in text


def test_a_clean_run_has_no_such_section() -> None:
    assert "Ölçülemeyen senaryolar" not in render([("x", [_result()])])


# --- eylem halüsinasyonu (P26) ---------------------------------------------------------


async def test_a_prose_answer_is_recorded_even_without_a_call(registry: Registry) -> None:
    """Çağrı üretilmeyen senaryonun metni artık kayboluyor değil (P26).

    Üretimdeki asıl hata tam burada yaşıyordu: hiç çağrı yapmadan "not eklendi" demek.
    Ölçüm 2026-08-13'e kadar bu dalda hiçbir şey kaydetmiyordu.
    """
    llm = FakeLLM(["Alışveriş listesi: Süt, ekmek, yumurta."])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("note_search"))
    )
    assert result.call is None
    assert result.answer == "Alışveriş listesi: Süt, ekmek, yumurta."
    assert not result.tool_correct


async def test_a_recorded_answer_enters_no_denominator(registry: Registry) -> None:
    """Kural 14: kanıt toplanıyor, ölçülmeyen şeye sayı verilmiyor. `answered`
    desteksiz sayı sayacının paydası ve bu satır oraya girmemeli."""
    llm = FakeLLM(["Not içinde süt ve ekmek yazıyordu, eminim."])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("note_search"))
    )
    summary = summarize("deneme", [result])
    assert not result.answer_graded
    assert summary.answered == 0
    assert summary.ungraded_answers == 1


async def test_the_graded_denominator_did_not_change(registry: Registry) -> None:
    """P26'nın bitti kriteri: hiçbir mevcut sayıcının paydası değişmemiş. Doğru çağrı +
    hazır sonuç, bugüne kadar olduğu gibi tek payda kaynağı."""
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli", "Otuz bir derece."])
    graded = await run_scenario(
        registry, llm, CallFormat.CLI, _weather_scenario({"temperature": 31})
    )
    no_call = await run_scenario(
        registry,
        FakeLLM(["Bilmiyorum."]),
        CallFormat.CLI,
        _weather_scenario({"temperature": 31}),
    )
    assert summarize("deneme", [graded, no_call]).answered == 1


async def test_ungraded_answers_are_listed_in_the_report(registry: Registry) -> None:
    llm = FakeLLM(["Süt, ekmek, yumurta yazmıştım."])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("note_search"))
    )
    report = render([("deneme", [result])])
    assert "Mekanik olarak yargılanmadı" in report
    assert "Süt, ekmek, yumurta yazmıştım." in report


async def test_a_quote_absent_from_every_source_is_counted(registry: Registry) -> None:
    """Dördüncü sayaç: `issues.md` #3'ün uydurması tırnak içinde bir listeydi."""
    llm = FakeLLM(['Nota "Süt, ekmek, yumurta" yazmıştım.'])
    result = await run_scenario(
        registry, llm, CallFormat.CLI, _scenario(ExpectedCall("note_search"))
    )
    assert result.unsupported_quotes == ("Süt, ekmek, yumurta",)
    assert summarize("deneme", [result]).unsupported_quotes == 1


async def test_a_quote_repeated_from_the_history_is_supported(registry: Registry) -> None:
    """Modelin kendi eski cümlesini tekrar etmesi uydurma değil; ölçülen **yeni** içerik."""
    llm = FakeLLM(['Nota "süt ve ekmek" yazmıştım.'])
    scenario = Scenario(
        "t-01",
        Kind.AYIRT_ETME,
        "Ne yazmıştın?",
        ExpectedCall("note_search"),
        history=(HistoryTurn("not al: süt ve ekmek", "Notu kaydettim."),),
    )
    result = await run_scenario(registry, llm, CallFormat.CLI, scenario)
    assert result.unsupported_quotes == ()


def test_the_report_says_the_first_two_counters_are_grammar_bound() -> None:
    """Kural 14: sıfır burada "gramer çalışıyor" demek, "model tool uydurmuyor" değil."""
    result = ScenarioResult(
        scenario_id="t-01",
        kind=Kind.TEK_TOOL,
        context=Context.YOK,
        call_format=CallFormat.CLI,
        model="sahte",
        output="",
        call=None,
        tool_correct=True,
        arguments_correct=None,
        unknown_tool=0,
        unknown_argument=0,
        corrections=0,
        tokens=0,
        seconds=0.0,
    )
    report = render([("deneme", [result])])
    assert GRAMMAR_BOUND_COUNTERS in report
    assert "gramerle sınırlı" in report


# --- üretim öneği (P27) ----------------------------------------------------------------

ROLE = "Sen Mayen'sin."


def test_the_measurement_prefix_is_unchanged(registry: Registry) -> None:
    """P27'nin en sert kuralı: eski önek **baytı baytına** duruyor. Değişirse
    `docs/faz2-olcum.md` ve `faz3-*` karşılaştırılamaz hâle gelir (P25.2)."""
    scenario = _scenario(text="Saat kaç?")
    messages = prefix_messages(
        registry,
        CallFormat.CLI,
        scenario,
        prefix=Prefix.OLCUM,
        role=None,
        tool_rows=True,
    )
    assert messages == [
        PromptMessage("system", system_prompt(registry, CallFormat.CLI)),
        PromptMessage("user", user_prompt(scenario)),
    ]


def test_summary_and_facts_do_not_leak_into_the_measurement_prefix(registry: Registry) -> None:
    """Ölçüm öneğinde `[özet]` diye bir yer yok; sessizce bir yere sıkıştırmak, iki
    kolonun farkını ölçülemez kılardı."""
    plain = _scenario(text="Saat kaç?")
    rich = replace(plain, summary="ÖZET-İŞARETİ", facts="OLGU-İŞARETİ")
    built = [
        prefix_messages(
            registry, CallFormat.CLI, scenario, prefix=Prefix.OLCUM, role=None, tool_rows=True
        )
        for scenario in (plain, rich)
    ]
    assert built[0] == built[1]


def test_the_production_prefix_comes_from_build_messages(registry: Registry) -> None:
    """İkinci bir kopya yazılmadı: üretimin sırası değişirse ölçüm de değişmeli.
    P27'nin varlık sebebi tam olarak bu ayrışmaydı."""
    scenario = replace(
        _scenario(text="Saat kaç?"),
        summary="kullanıcı İzmir'de oturuyor",
        facts="- kullanıcı çayı şekersiz içer (bayat olabilir)",
    )
    messages = prefix_messages(
        registry, CallFormat.CLI, scenario, prefix=Prefix.URETIM, role=ROLE, tool_rows=True
    )
    assert list(messages) == list(
        build_messages(
            agent_system_prompt(registry, CallFormat.CLI, role=ROLE),
            context=ContextBlock(now=NOW, facts=scenario.facts),
            user=scenario.text,
            summary=scenario.summary,
            history=[],
        )
    )


def test_the_production_prefix_carries_role_summary_and_facts(registry: Registry) -> None:
    """Üç blok da ölçümde bugüne kadar hiç yoktu; P27'nin ölçtüğü şey bu."""
    scenario = replace(
        _scenario(text="Saat kaç?"),
        summary="kullanıcı İzmir'de oturuyor",
        facts="- kullanıcı çayı şekersiz içer (bayat olabilir)",
    )
    text = "\n".join(
        m.content
        for m in prefix_messages(
            registry, CallFormat.CLI, scenario, prefix=Prefix.URETIM, role=ROLE, tool_rows=True
        )
    )
    assert ROLE in text
    assert "[özet]" in text
    assert "bayat olabilir" in text
    assert "[bağlam]" in text


def test_the_production_prefix_refuses_to_run_without_a_role(registry: Registry) -> None:
    """Rolün kodda yedeği yok (§8.1); sessiz bir varsayılan, dosyayı düzenleyip hiçbir
    şeyin değişmediğini görmenin yolu olurdu."""
    with pytest.raises(ValueError, match="rol"):
        prefix_messages(
            registry,
            CallFormat.CLI,
            _scenario(),
            prefix=Prefix.URETIM,
            role=None,
            tool_rows=True,
        )


async def test_the_prefix_is_recorded_on_the_row(registry: Registry) -> None:
    """Etiket değil satır: iki önek aynı raporda yan yana duruyor."""
    llm = FakeLLM([f"{CALL_PREFIX}date_time"])
    result = await run_scenario(
        registry,
        llm,
        CallFormat.CLI,
        _scenario(ExpectedCall("date_time")),
        prefix=Prefix.URETIM,
        role=ROLE,
    )
    assert result.prefix is Prefix.URETIM


async def test_the_report_names_the_prefix_and_the_role_file(registry: Registry) -> None:
    llm = FakeLLM([f"{CALL_PREFIX}date_time"])
    result = await run_scenario(
        registry,
        llm,
        CallFormat.CLI,
        _scenario(ExpectedCall("date_time")),
        prefix=Prefix.URETIM,
        role=ROLE,
    )
    report = render([("deneme", [result])], role_paths=[Path("config/rol.txt")])
    assert Prefix.URETIM.value in report
    assert "config/rol.txt" in report


async def test_summary_numbers_are_supported_claims(registry: Registry) -> None:
    """Özetten okunan bir sayı uydurma değil: önek de bir kaynak (P27)."""
    llm = FakeLLM([f"{CALL_PREFIX}weather --city Denizli", "Üç yıldır İzmir'de, 3 yıl."])
    scenario = replace(
        _weather_scenario({"temperature": 31}), summary="kullanıcı 3 yıldır İzmir'de"
    )
    result = await run_scenario(
        registry, llm, CallFormat.CLI, scenario, prefix=Prefix.URETIM, role=ROLE
    )
    assert result.unsupported_numbers == ()

"""Oturum ölçümünün koşucusu (Faz A/A2). GPU yok: `FakeLLM` betikle sürüyor.

Ölçülen şey modelin davranışı değil, **aracın** davranışı: turların birbirinin üstüne
biriktiği, geçmişin üretimin sırasıyla yazıldığı ve kırılma noktasının doğru sayıldığı.
Bir ölçüm aracının kendi hatası, ölçtüğü şeyin hatası gibi okunur.
"""

from dataclasses import replace
from pathlib import Path

import pytest
from evals.session import SessionResult, TurnResult, run_session
from evals.sessions import SessionScenario, Turn

from mayen.adapters.errors import ServiceUnavailableError
from mayen.adapters.fakes.llm import FakeLLM
from mayen.agent.calls import CallFormat
from mayen.config import Config
from mayen.tools.catalog import builtin_registry


@pytest.fixture
def config(tmp_path: Path) -> Config:
    role = tmp_path / "rol.txt"
    role.write_text("Sen bir asistansın.", encoding="utf-8")
    return replace(Config(), role_path=role, assume_owner=True)


_SCENARIO = SessionScenario(
    id="test-01",
    turns=(
        Turn("bugün derslerim neler", "course_schedule", {"gün": "Pazar"}),
        Turn("bugün derslerim neler", "course_schedule", {"gün": "Pazar"}),
        Turn("hey", None),
    ),
)


async def _run(config: Config, llm: FakeLLM) -> SessionResult:
    return await run_session(
        config,
        llm,
        builtin_registry(config),
        _SCENARIO,
        call_format=CallFormat.CLI,
        digest_on=False,
    )


async def test_the_models_own_answer_becomes_the_next_turns_history(config: Config) -> None:
    """A2'nin varlık sebebi: geçmişi elle yazan bir küme bu döngüyü kuramaz."""
    llm = FakeLLM(
        [
            "<tool> course_schedule",
            "Bugün Pazar, dersin yok.",
            "Bugün Pazar, dersin yok.",
            "Buradayım.",
        ]
    )

    result = await _run(config, llm)

    # Üçüncü turun öneği (dördüncü üretim) ilk turun cevabını **ve tool adımını** taşıyor.
    # Adım iki satır: çağrı `assistant`, sonuç `tool` — üretimin biçiminin aynısı
    # (`turn/runner.py`, 2026-08-16). Ölçüm üretimin kurmadığı bir öneği kurarsa
    # ölçtüğü şey üretim olmaz (P27).
    third = "\n".join(m.content for m in llm.calls[3])
    assert "Bugün Pazar, dersin yok." in third
    assert "<tool> course_schedule" in third
    roles = [m.role for m in llm.calls[3]]
    assert "tool" in roles
    assert [t.call.name if t.call else None for t in result.turns] == [
        "course_schedule",
        None,
        None,
    ]


async def test_the_first_missed_call_is_the_measured_number(config: Config) -> None:
    """Oran değil kırılma noktası: "yarısını kaçırdı" ile "ikinci turdan sonra hiç
    çağırmadı" aynı yüzdeyi verir, aynı arızayı anlatmaz."""
    llm = FakeLLM(
        [
            "<tool> course_schedule",
            "Bugün Pazar, dersin yok.",
            "Bugün Pazar, dersin yok.",
            "Buradayım.",
        ]
    )

    result = await _run(config, llm)

    assert result.first_missed == 2
    assert result.called == 1
    assert len(result.wanted) == 2
    assert result.over_called == 0


async def test_an_unexpected_call_is_counted_separately(config: Config) -> None:
    """Negatif kontrol: yalnızca çağrı oranına bakan bir ölçüm, her tura tool çağıran bir
    modeli kusursuz gösterirdi."""
    llm = FakeLLM(
        [
            "<tool> course_schedule",
            "Bugün Pazar.",
            "<tool> course_schedule",
            "Bugün Pazar.",
            "<tool> date_time",
            "Saat üç.",
        ]
    )

    result = await _run(config, llm)

    assert result.called == 2
    assert result.first_missed is None
    assert result.over_called == 1


async def test_a_dropped_stream_ends_the_turn_not_the_session(config: Config) -> None:
    """`issues.md` #2 bu koşunun içinde görüldü. Düşen tur kaydediliyor ve oturum sürüyor;
    geçmişine hiçbir cevap yazılmıyor (olmayan bir cevabı kaydetmek, sonraki turların
    gördüğü konuşmayı uydurmak olurdu)."""
    llm = FakeLLM(["<tool> course_schedule", "Bugün Pazar.", "Buradayım.", "Buradayım."])

    result = await _failing_second_turn(config, llm)

    assert result.turns[1].errors
    assert result.turns[1].answer == ""
    assert result.failed_turns == 1
    assert len(result.turns) == 3


async def _failing_second_turn(config: Config, llm: FakeLLM) -> SessionResult:
    """Yalnızca ikinci turun **üretimi** düşüyor; sayaç ucu ve sonraki turlar sağlam.

    `FakeLLM.available` kapatılamıyor: `count_tokens` de ona bakıyor ve kapatmak üçüncü
    turun penceresini de düşürürdü — ölçülmek istenen şey tek bir turun düşmesi.
    """
    original = llm.stream
    seen = 0

    def stream(*args: object, **kwargs: object) -> object:
        nonlocal seen
        seen += 1
        # Tur 1 iki üretim harcıyor (çağrı + yanıt); tur 2'nin iki denemesi de düşsün.
        if seen in (3, 4):
            raise ServiceUnavailableError("fake-llm", "servis kapalı")
        return original(*args, **kwargs)  # type: ignore[arg-type]

    llm.stream = stream  # type: ignore[method-assign,assignment]
    return await _run(config, llm)


def test_a_turn_result_knows_when_no_call_was_the_right_answer() -> None:
    """`expected is None` satırlarında `hit`, "çağrı gelmedi" demek."""
    turn = TurnResult(
        index=1,
        user="hey",
        expected=None,
        call=None,
        answer="Buradayım.",
        prompt_tokens=10,
        summary_chars=0,
        facts=0,
    )
    assert turn.hit is True

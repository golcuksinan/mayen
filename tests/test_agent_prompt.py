"""§8.1'in sabit önek düzeni."""

from pathlib import Path

import pytest

from mayen.adapters.llm import PromptMessage
from mayen.agent.calls import CallFormat
from mayen.agent.prompt import ContextBlock, build_messages, load_role, system_prompt
from mayen.config import ConfigError
from mayen.tools.catalog import builtin_registry

ROLE = "Sen Mayen'sin."


@pytest.fixture
def system() -> str:
    return system_prompt(builtin_registry(), CallFormat.CLI, role=ROLE)


def test_system_prompt_is_byte_stable() -> None:
    """Kural 3: aynı defter ve aynı biçim, baytı baytına aynı önek."""
    first = system_prompt(builtin_registry(), CallFormat.CLI, role=ROLE)
    second = system_prompt(builtin_registry(), CallFormat.CLI, role=ROLE)
    assert first == second


def test_system_prompt_carries_role_syntax_and_catalog(system: str) -> None:
    assert "Mayen" in system
    assert "--" in system  # çağrı sözdizimi
    assert "weather" in system  # katalog


def test_language_rule_goes_last_inside_the_system_prompt() -> None:
    """Sabit öneğin sonu, yani değişken içeriğe değmeden ulaşılabilen son nokta.

    Bir adım ötesi ölçüldü ve pahalıydı: kullanıcı mesajından sonraya konan kural önbellek
    isabetini tamamen düşürüyor (senaryo başına 22 → 1631 jeton, `docs/faz7-rol.md`).
    """
    prompt = system_prompt(builtin_registry(), CallFormat.CLI, role=ROLE, language_rule="KURAL")
    assert prompt.endswith("KURAL")
    assert prompt.startswith(ROLE)


def test_language_rule_is_omitted_when_absent(system: str) -> None:
    assert system == system_prompt(builtin_registry(), CallFormat.CLI, role=ROLE)


def test_order_is_system_summary_history_context_user() -> None:
    history = (
        PromptMessage(role="user", content="dün ne demiştim"),
        PromptMessage(role="assistant", content="hava soracaktın"),
    )
    messages = build_messages(
        "SİSTEM",
        summary="ÖZET",
        history=history,
        context=ContextBlock(now="2026-08-09T10:00:00Z"),
        user="hava nasıl",
    )
    assert [m.content for m in messages] == [
        "SİSTEM",
        "[özet]\nÖZET",
        "dün ne demiştim",
        "hava soracaktın",
        messages[4].content,
        "hava nasıl",
    ]
    assert messages[4].content.startswith("[bağlam]")


def test_summary_is_omitted_when_absent() -> None:
    messages = build_messages("SİSTEM", context=ContextBlock(now="Z"), user="merhaba")
    assert [m.role for m in messages] == ["system", "user", "user"]


def test_only_the_first_message_is_system() -> None:
    """Qwen3.6'nın şablonu baştan sonra gelen `system` mesajında istisna atıyor ve
    llama-server 500 döndürüyor; tur modelin ilk çağrısında ölüyordu. Sıra korunuyor,
    yalnızca rol değişti (gerekçe `agent/prompt.py`'nin başlığında)."""
    messages = build_messages(
        "SİSTEM",
        summary="ÖZET",
        history=(PromptMessage(role="assistant", content="dün"),),
        context=ContextBlock(now="Z"),
        user="merhaba",
        turn=(PromptMessage(role="tool", content="18 derece"),),
    )
    assert messages[0].role == "system"
    assert all(m.role != "system" for m in messages[1:])


def test_variable_content_only_in_context_block() -> None:
    """Değişken içerik öneki kaydırmaz: yalnızca bağlam bloğu değişir."""
    first = build_messages(
        "SİSTEM",
        summary="ÖZET",
        context=ContextBlock(now="A", speaker="Sinan"),
        user="hava nasıl",
    )
    second = build_messages(
        "SİSTEM",
        summary="ÖZET",
        context=ContextBlock(now="B", speaker="Ayşe"),
        user="hava nasıl",
    )
    assert first[:-2] == second[:-2]
    assert first[-2] != second[-2]
    assert first[-1] == second[-1]


def test_context_block_omits_unknown_speaker() -> None:
    assert "konuşan" not in ContextBlock(now="Z").render()
    assert "konuşan: Sinan" in ContextBlock(now="Z", speaker="Sinan").render()


def test_turn_messages_come_after_the_user_sentence() -> None:
    """§8.2: tool sonucu ayrı bir istek değil, aynı öneğin devamı."""
    turn = (
        PromptMessage(role="assistant", content="<tool_call>weather --city Ankara"),
        PromptMessage(role="tool", content="18 derece"),
    )
    messages = build_messages(
        "SİSTEM", context=ContextBlock(now="Z"), user="hava nasıl", turn=turn
    )
    assert messages[-2:] == turn
    assert messages[-3].content == "hava nasıl"


def test_role_comes_from_the_file_and_the_catalog_still_from_the_registry(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rol.txt"
    path.write_text("Sen Zeynep'sin. Kısa ve alaycı konuş.\n", encoding="utf-8")
    prompt = system_prompt(builtin_registry(), CallFormat.CLI, role=load_role(path))
    assert prompt.startswith("Sen Zeynep'sin. Kısa ve alaycı konuş.")
    assert "weather" in prompt  # katalog hâlâ defterden


def test_missing_or_empty_role_file_is_an_error(tmp_path: Path) -> None:
    """Sessiz varsayılana düşmek, kişiliği değiştirdiğini sanan kurulumu gizlerdi."""
    with pytest.raises(ConfigError):
        load_role(tmp_path / "yok.txt")
    empty = tmp_path / "bos.txt"
    empty.write_text("   \n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_role(empty)


def test_role_has_no_copy_in_the_code() -> None:
    """Tek kaynak dosya: kodda yedek bir kişilik metni kalmadı, yoksa ikisi ayrışırdı."""
    import inspect

    from mayen.agent import prompt

    assert "Sen Mayen'sin" not in inspect.getsource(prompt)

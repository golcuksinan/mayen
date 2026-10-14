"""Yazılı kanal (§7, §13): mesaj biçimi, serileştirici, hattın iki ucu, cihaz kimliği."""

import json
import stat
from collections.abc import Sequence
from pathlib import Path

import pytest
from pipecat.frames.frames import (
    Frame,
    InputTransportMessageFrame,
    LLMFullResponseEndFrame,
    LLMMessagesAppendFrame,
    LLMTextFrame,
    OutputTransportMessageFrame,
    TextFrame,
    TTSSpeakFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.tests.utils import run_test

import mayen.adapters.channel.tailscale as tailscale
from fakes import MemoryEventLog
from mayen.adapters.channel.tailscale import TailscaleIdentity
from mayen.core.events import Recorder, SystemClock
from mayen.core.turns import Turns
from mayen.pipeline.session import Sessions, TriggerGate
from mayen.pipeline.text import TextInput, TextOutput, WireSerializer
from mayen.ports.channels import MessageKind, WireMessage
from mayen.ports.confirmation import Answer
from mayen.ports.tools import Caller, Role
from mayen.ports.triggers import Fate, Priority, TriggerSource

OWNER = Caller(Role.OWNER, "1", has_personal_device=True)


class Confirmations:
    def __init__(self, awaiting: bool) -> None:
        self.awaiting = awaiting
        self.answers: list[Answer] = []

    def answer(self, answer: Answer) -> None:
        self.answers.append(answer)


def test_message_round_trip_keeps_turkish_text() -> None:
    message = WireMessage(MessageKind.TEXT, "dişçi yarın")
    assert "dişçi" in message.encode()
    assert WireMessage.decode(message.encode()) == message
    assert WireMessage.decode('{"type": "response_end"}') == WireMessage(
        MessageKind.RESPONSE_END
    )


@pytest.mark.parametrize("raw", ["not json", "[]", '{"text": "x"}', '{"type": "nope"}'])
def test_malformed_message_is_a_value_error(raw: str) -> None:
    with pytest.raises(ValueError):
        WireMessage.decode(raw)


async def test_serializer_speaks_only_wire_messages() -> None:
    serializer = WireSerializer()
    out = OutputTransportMessageFrame(message=WireMessage(MessageKind.TEXT, "a"))
    assert json.loads(str(await serializer.serialize(out))) == {"type": "text", "text": "a"}
    assert await serializer.serialize(TextFrame("a")) is None
    frame = await serializer.deserialize('{"type": "text", "text": "selam"}')
    assert isinstance(frame, InputTransportMessageFrame)
    assert frame.message == WireMessage(MessageKind.TEXT, "selam")
    assert await serializer.deserialize("bozuk") is None


async def written(
    text: str, confirmations: Confirmations, log: MemoryEventLog
) -> Sequence[Frame]:
    sessions = Sessions(Turns(dict.fromkeys(TriggerSource, Fate.CANCEL)), Priority.NORMAL)
    gate = TriggerGate(
        "s1",
        sessions,
        lambda _: OWNER,
        Recorder(log, SystemClock()),
        settle_s=0.1,
        response_timeout_s=0.3,
    )
    text_input = TextInput("s1", sessions, confirmations, OWNER, Priority.HIGH)
    message = WireMessage(MessageKind.TEXT, text)
    down, _ = await run_test(
        Pipeline([text_input, gate]),
        frames_to_send=[InputTransportMessageFrame(message=message)],
    )
    return down


async def test_written_message_opens_a_text_turn_for_the_device_owner() -> None:
    log = MemoryEventLog()
    down = await written("selam", Confirmations(awaiting=False), log)
    [append] = [f for f in down if isinstance(f, LLMMessagesAppendFrame)]
    assert append.messages == [{"role": "user", "content": "selam"}]
    assert not any(isinstance(f, InputTransportMessageFrame) for f in down)
    [started] = [e for e in log.events if e.body.get("source") == "text"]
    assert started.body["priority"] == "high"


async def test_written_message_while_awaiting_is_only_an_answer() -> None:
    log = MemoryEventLog()
    confirmations = Confirmations(awaiting=True)
    down = await written("evet", confirmations, log)
    assert confirmations.answers == [Answer("evet", "1")]
    # Tur açılmaz, model çalışmaz (§5.4: kapalı durum).
    assert not any(isinstance(f, LLMMessagesAppendFrame) for f in down)
    assert not [e for e in log.events if e.body.get("source") == "text"]


async def test_reply_and_spoken_question_reach_the_client_as_messages() -> None:
    down, _ = await run_test(
        TextOutput(),
        frames_to_send=[
            LLMTextFrame("Mer"),
            LLMTextFrame("haba."),
            LLMFullResponseEndFrame(),
            LLMFullResponseEndFrame(),  # yalnızca tool çağıran cevap: istemciye gitmez
            TTSSpeakFrame("Silinsin mi?"),
        ],
    )
    sent = [f.message for f in down if isinstance(f, OutputTransportMessageFrame)]
    assert sent == [
        WireMessage(MessageKind.TEXT, "Mer"),
        WireMessage(MessageKind.TEXT, "haba."),
        WireMessage(MessageKind.RESPONSE_END),
        WireMessage(MessageKind.TEXT, "Silinsin mi?"),
        WireMessage(MessageKind.RESPONSE_END),
    ]
    # Metin hatta da ilerler: asistan toplayıcısı geçmişi onlardan yazar.
    assert [f.text for f in down if isinstance(f, LLMTextFrame)] == ["Mer", "haba."]


def fake_tailscale(tmp_path: Path, body: str) -> str:
    script = tmp_path / "tailscale"
    script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


async def test_device_is_the_tailscale_node(tmp_path: Path) -> None:
    command = fake_tailscale(
        tmp_path, """echo '{"Node": {"StableID": "nStable1", "Name": "phone"}}'"""
    )
    assert await TailscaleIdentity(command).device("100.64.0.2") == "nStable1"


@pytest.mark.parametrize(
    "body",
    [
        "exit 1",  # Tailscale kapalı ya da adres tailnet'ten değil
        "echo 'not json'",
        """echo '{"Node": {}}'""",
        """echo '{"Node": {"StableID": ""}}'""",
    ],
)
async def test_unverifiable_connection_has_no_device(tmp_path: Path, body: str) -> None:
    assert await TailscaleIdentity(fake_tailscale(tmp_path, body)).device("1.2.3.4") is None


async def test_missing_or_hung_tailscale_has_no_device(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert await TailscaleIdentity(str(tmp_path / "none")).device("1.2.3.4") is None
    monkeypatch.setattr(tailscale, "WHOIS_TIMEOUT_S", 0.05)
    hung = fake_tailscale(tmp_path, "sleep 5")
    assert await TailscaleIdentity(hung).device("1.2.3.4") is None

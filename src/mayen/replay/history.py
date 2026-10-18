"""Kayıtlardan modelin o gün gördüğü geçmiş (§14): olay kaydı ve transkript, zaman sırasıyla.

Geçmişe giren her şey kayıtlardan kurulur, ayrıca saklanmaz:

- Kişinin sözü transkriptten. Yazı turunun başladığı an girer (sıradaki yazı da öyle);
  ses, duyulduğu an. Duyulmayan söz (`muted`) ve onaya verilen cevap modele gitmemişti.
- Mayen'in sözü transkriptten; onay sorusu da.
- Tetikleyicinin mesajı turun başlangıç olayından ve bağlı olduğu kayıtlardan.
- Tool çağrısı ve sonucu olaylardan. Sonuç, modelin gördüğü gibi yetki süzgecinden geçer;
  onay bekleyen çağrının sonucu "onay bekleniyor"dur, asıl sonuç onay mesajıyla gelir.

Baştan başlayan yazılı tur, kesilen turun mesajını geçmişe yeniden ekler; burada da öyle.
Bilinen fark: bir cevaptaki birden çok çağrı ayrı cevaplar olarak kurulur. Unut (§11.4)
geldiğinde unutulan kayıt burada düşer.
"""

import json
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mayen.core.policy import PolicyTable, filter_records
from mayen.core.timers import local
from mayen.pipeline.tools import AWAITING_CONFIRMATION, to_model
from mayen.ports.devices import Capability
from mayen.ports.events import Event, EventKind, ref
from mayen.ports.timers import TimerState, TimerStore
from mayen.ports.tools import Caller, Record, Role, Sensitivity, Status, ToolResult, Verdict
from mayen.ports.transcript import Party, Utterance
from mayen.ports.triggers import Priority, TriggerSource, TurnId

type Message = dict[str, Any]

# Kişinin rolü ve kimliğinden çağıran; kişisel cihazı olup olmadığı profilden.
type CallerOf = Callable[[Role, str | None], Caller]
# Kaydedilmiş sözün kişisinden başına yazılan ad (§8.1); hattaki etiketin aynısı.
type LabelOf = Callable[[str | None], str]
type TableOf = Callable[[TriggerSource], PolicyTable]


@dataclass(frozen=True)
class TurnInfo:
    id: TurnId
    session: str
    time: datetime
    source: TriggerSource
    priority: Priority
    requester: Caller
    device_person: str | None  # oturumun cihazının kişisi; kimse istemediyse dinleyen
    capabilities: tuple[Capability, ...] = ()  # oturumun cihazının yetenekleri (§9.7)


def utterance_ref(utterance: Utterance) -> str:
    return ref("utterance", utterance.id)


def result_of(body: Mapping[str, Any]) -> ToolResult:
    """Olay gövdesindeki sonuç zarfı, yetki süzgecinden önceki hâliyle (§5.5)."""
    raw = body["result"]
    return ToolResult(
        Status(raw["status"]),
        raw["data"],
        tuple(Record(Sensitivity(r["sensitivity"]), r["data"]) for r in raw["records"]),
        raw["error"],
        raw["withheld"],
        raw.get("relay", True),  # alandan önceki kayıtlarda yok
    )


class Records:
    """Bir oturumun kayıtları; turlar ve geçmiş bundan okunur."""

    def __init__(
        self,
        events: Sequence[Event],
        utterances: Sequence[Utterance],
        timers: TimerStore,
        caller_of: CallerOf,
        label_of: LabelOf | None = None,
    ) -> None:
        self.events = events
        self._label_of = label_of
        self.utterances = utterances
        self._timers = timers
        stt = [e for e in events if e.header.kind is EventKind.STT_SEGMENT]
        self._muted = {r: bool(e.body.get("muted")) for e in stt for r in e.header.related}
        closed = [e for e in events if e.header.kind is EventKind.CONFIRMATION_CLOSED]
        self._answers = {r for e in closed for r in e.header.related}
        self.turns = {t.id: t for t in self._turns(caller_of)}

    def voiced(self, utterance: Utterance) -> bool:
        return utterance_ref(utterance) in self._muted

    def _turns(self, caller_of: CallerOf) -> Iterator[TurnInfo]:
        # Sesli turun isteyeni tur açılırken bilinmez; bitiş olayı turun sonunda kim
        # sayıldığını taşır (§6: turun bütün sözlerinden).
        ended = {
            e.header.turn_id: e.body["requester"]
            for e in self.events
            if e.header.kind in (EventKind.TURN_FINISHED, EventKind.TURN_INTERRUPTED)
            and isinstance(e.body.get("requester"), dict)
        }
        for e in self.events:
            h = e.header
            if h.kind is not EventKind.TURN_STARTED or h.turn_id is None or h.session is None:
                continue
            source = TriggerSource(e.body["source"])
            requester = e.body.get("requester", {})
            if source is TriggerSource.VOICE and h.turn_id in ended:
                requester = ended[h.turn_id]
            role, person = Role(requester.get("role", Role.UNKNOWN)), requester.get("person_id")
            if source is TriggerSource.VOICE and h.turn_id not in ended:
                # Bitiş olayında isteyen yoksa (eski kayıt) ilk sözün konuşanıdır.
                first = next(
                    (
                        u
                        for u in self.utterances
                        if u.turn_id == h.turn_id and u.party is Party.PERSON and u.role
                    ),
                    None,
                )
                if first is not None and first.role is not None:
                    role, person = first.role, first.person_id
            yield TurnInfo(
                h.turn_id,
                h.session,
                h.time,
                source,
                Priority(e.body["priority"]),
                caller_of(role, person),
                e.body.get("device_person"),
                tuple(Capability(c) for c in e.body.get("capabilities", ())),
            )

    def history(self, table: TableOf, until: datetime | None = None) -> list[Message]:
        """`until`'den önce modelin geçmişine yazılmış mesajlar, yazıldıkları sırayla."""
        texts = {
            u.turn_id: u
            for u in self.utterances
            if u.party is Party.PERSON
            and u.turn_id is not None
            and not self.voiced(u)
            and utterance_ref(u) not in self._answers
        }
        verdicts: dict[str | None, str | None] = {}
        restarted: Utterance | None = None  # baştan başlayacak yazılı turun mesajı
        out: list[Message] = []
        for time, item in self._timeline():
            if until is not None and time >= until:
                break
            if isinstance(item, Utterance):
                out.extend(self._spoken(item, out))
                continue
            h, body = item.header, item.body
            turn = None if h.turn_id is None else self.turns.get(h.turn_id)
            match h.kind:
                case EventKind.TURN_STARTED if turn is not None:
                    if turn.source is TriggerSource.TEXT:
                        # Yeni kimlikle baştan başlayan turun kendi sözü yoktur (§5.3).
                        text = texts.get(turn.id) or restarted
                        restarted = None
                        if text is not None:
                            out.append({"role": "user", "content": self._labelled(text)})
                    elif turn.source is not TriggerSource.VOICE:
                        out.append({"role": "developer", "content": self._trigger(item, turn)})
                case EventKind.TURN_INTERRUPTED if turn is not None:
                    if body.get("fate") == "restart" and turn.source is TriggerSource.TEXT:
                        restarted = texts.get(turn.id) or restarted
                    if body.get("fate") == "cancel":
                        note = json.dumps({"interrupted": turn.source.value})
                        out.append({"role": "developer", "content": note})
                case EventKind.TOOL_REQUESTED:
                    call_id, verdict = body["call_id"], body["verdict"]
                    verdicts[call_id] = verdict
                    out.append(_call_message(call_id, body["tool"], body["arguments"]))
                    if verdict == Verdict.CONFIRM.value:
                        out.append(_tool_message(call_id, {"status": AWAITING_CONFIRMATION}))
                case EventKind.TOOL_FINISHED:
                    call_id = body.get("call_id")
                    if call_id not in verdicts or verdicts[call_id] == Verdict.CONFIRM.value:
                        continue  # onaylı çağrının sonucu onay mesajıyla gelir
                    result = result_of(body)
                    if verdicts[call_id] == Verdict.ALLOW.value and turn is not None:
                        result = filter_records(result, turn.requester, table(turn.source))
                    out.append(_tool_message(call_id, to_model(result)))
                case EventKind.CONFIRMATION_CLOSED:
                    content = json.dumps(dict(body), ensure_ascii=False)
                    out.append({"role": "developer", "content": content})
        return out

    def _timeline(self) -> list[tuple[datetime, Event | Utterance]]:
        items: list[tuple[datetime, Event | Utterance]] = [
            (e.header.time, e) for e in self.events
        ]
        items += [(u.time, u) for u in self.utterances]
        # Sıralama kararlıdır: aynı andaki kayıtlar kendi depolarındaki sırayla kalır.
        return sorted(items, key=lambda item: item[0])

    def _spoken(self, utterance: Utterance, out: list[Message]) -> list[Message]:
        if utterance.party is Party.ASSISTANT:
            return [{"role": "assistant", "content": utterance.text}]
        record = utterance_ref(utterance)
        if record not in self._muted or self._muted[record] or record in self._answers:
            return []  # yazı turuyla girer; duyulmayan ve cevap olan söz modele gitmedi
        last = out[-1] if out else None
        text = self._labelled(utterance)
        if last is not None and last["role"] == "user" and last.get("voice"):
            # Bir sözün segmentleri tek kullanıcı mesajıdır; her segment kendi etiketiyle.
            last["content"] = f"{last['content']} {text}"
            return []
        return [{"role": "user", "content": text, "voice": True}]

    def _labelled(self, utterance: Utterance) -> str:
        if self._label_of is None:
            return utterance.text
        return f"{self._label_of(utterance.person_id)}: {utterance.text}"

    def _trigger(self, started: Event, turn: TurnInfo) -> str:
        """Hattın tetikleyiciden kurduğu etiketli mesaj (§2.1), bağlı kayıtlardan."""
        timers = [
            t
            for r in started.header.related
            if r.startswith("timer:") and (t := self._timers.get(r.removeprefix("timer:")))
        ]
        message: dict[str, Any] = {
            "trigger": turn.source.value,
            "priority": turn.priority.value,
            "content": "",
        }
        if timers and timers[0].state is TimerState.MISSED:
            message["details"] = {
                "missed": [{"text": t.text, "due": local(t.due)} for t in timers]
            }
        elif timers:
            message["content"] = timers[0].text
            message["details"] = {"due": local(timers[0].due)}
        return json.dumps(message, ensure_ascii=False)


def clean(messages: Sequence[Message]) -> list[Message]:
    """Kurulurken kullanılan işaretler modele gitmez."""
    return [{k: v for k, v in m.items() if k != "voice"} for m in messages]


def _call_message(call_id: str | None, tool: str, arguments: Any) -> Message:  # noqa: ANN401
    return {
        "role": "assistant",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": tool,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }
        ],
    }


def _tool_message(call_id: str | None, result: Mapping[str, Any]) -> Message:
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": json.dumps(dict(result), ensure_ascii=False),
    }

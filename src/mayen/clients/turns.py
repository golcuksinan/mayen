"""Turların okunur zaman çizelgesi: kim ne dedi, hangi tool ne döndü (`mayen-turns`).

Log değil, panelin terminal karşılığıdır: içerik loga girmez (§14), burada panelin ucundan
(`/events`) okunur ve veritabanı açılmaz (§3). Unutulan ya da silinen bir kayıt burada da
görünmez. Panel gibi yalnızca sahibin cihazından açılır.

Önce istenen andan bu yana olanlar yazılır; `--follow` ile ardından canlı kayıtlar da.
"""

import argparse
import asyncio
import json
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from mayen.ports.events import Event, EventKind, stamp
from mayen.ports.panel import decode
from mayen.ports.transcript import Party, Utterance

DEFAULT_URL = "ws://127.0.0.1:8765/events"
DEFAULT_MINUTES = 60
INDENT = "  "
OUTSIDE = "(outside a turn) "


def _clock(moment: datetime) -> str:
    return f"{moment.astimezone():%H:%M:%S}"


def _compact(value: Any) -> str:  # noqa: ANN401
    return json.dumps(value, ensure_ascii=False)


def _who(role: str | None, person_id: str | None) -> str:
    who = role or "?"
    return who if person_id is None else f"{who}#{person_id}"


def _requester(body: Mapping[str, Any]) -> str:
    raw = body.get("requester") or {}
    return _who(raw.get("role"), raw.get("person_id"))


def _result(result: Mapping[str, Any]) -> str:
    data = dict(result.get("data") or {})
    if result.get("records"):
        data["records"] = len(result["records"])
    if result.get("withheld"):
        data["withheld"] = result["withheld"]
    status = str(result.get("status", "?"))
    out = status if not data else f"{status} {_compact(data)}"
    error = result.get("error")
    return out if error is None else f"{out} — {error}"


@dataclass
class Timeline:
    """Gelen kayıtları satıra çevirir. Konuşmacı puanı sözün STT olayındadır: geçmişte ikisi
    birlikte okunur; canlıda söz olayından önce gelir ve puansız yazılır."""

    _scores: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    _verdicts: dict[str, str] = field(default_factory=dict)

    def lines(self, items: Iterable[Event | Utterance]) -> Iterator[str]:
        ordered = sorted(items, key=lambda i: i.header.time if isinstance(i, Event) else i.time)
        for item in ordered:
            if isinstance(item, Event):
                self._learn(item)
        for item in ordered:
            line = self._event(item) if isinstance(item, Event) else self._utterance(item)
            if line is not None:
                yield line

    def _learn(self, event: Event) -> None:
        if event.header.kind is EventKind.STT_SEGMENT:
            for record in event.header.related:
                self._scores[record] = event.body
        elif event.header.kind is EventKind.TOOL_REQUESTED:
            self._verdicts[str(event.body.get("call_id"))] = str(event.body.get("verdict"))

    def _event(self, event: Event) -> str | None:
        header, body = event.header, event.body
        at = _clock(header.time)
        kind = header.kind
        if kind is EventKind.TURN_STARTED:
            capabilities = ",".join(body.get("capabilities", ())) or "-"
            return (
                f"{at} turn · {body.get('source', '?')} · {header.session} · "
                f"device: {capabilities}"
            )
        if kind is EventKind.TURN_FINISHED:
            unanswered = " · unanswered" if body.get("unanswered") else ""
            return f"{at} turn finished · requester: {_requester(body)}{unanswered}"
        if kind is EventKind.TURN_INTERRUPTED:
            fate = body.get("fate", "?")
            return f"{at} turn interrupted ({fate}) · requester: {_requester(body)}"
        if kind is EventKind.TOOL_FINISHED:
            verdict = self._verdicts.get(str(body.get("call_id")))
            shown = f" [{verdict}]" if verdict not in (None, "allow", "None") else ""
            arguments = _compact(body.get("arguments", {}))
            result = _result(body.get("result", {}))
            return f"{INDENT}{at} {body.get('tool')} {arguments}{shown} → {result}"
        if kind is EventKind.CONFIRMATION_CLOSED:
            calls = ", ".join(c.get("tool", "?") for c in body.get("calls", ()))
            return f"{INDENT}{at} confirmation {body.get('confirmation', '?')}: {calls}"
        return None

    def _utterance(self, utterance: Utterance) -> str:
        at = _clock(utterance.time)
        if utterance.party is Party.ASSISTANT:
            cut = " (cut)" if utterance.interrupted else ""
            return f"{INDENT}{at} Mayen{cut}  {utterance.text}"
        where = INDENT if utterance.turn_id is not None else OUTSIDE
        role = None if utterance.role is None else utterance.role.value
        who = _who(role, utterance.person_id)
        segment = self._scores.get(f"utterance:{utterance.id}", {})
        score = segment.get("speaker_score")
        if score is not None:
            who = f"{who} {score:.2f}"
        muted = " (not heard)" if segment.get("muted") else ""
        return f"{where}{at} {who}{muted}  {utterance.text}"


def since_of(text: str | None, now: datetime) -> datetime:
    """`HH:MM` bugünün yerel saati, yoksa ISO tarih-saat; verilmezse son bir saat."""
    if text is None:
        return now - timedelta(minutes=DEFAULT_MINUTES)
    local = now.astimezone()
    try:
        moment = datetime.strptime(text, "%H:%M")
        return local.replace(hour=moment.hour, minute=moment.minute, second=0, microsecond=0)
    except ValueError:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo is not None else parsed.astimezone()


async def run(url: str, since: datetime, follow: bool) -> None:
    timeline = Timeline()
    history: list[Event | Utterance] = []
    async with connect(f"{url}?since={stamp(since.astimezone(UTC))}") as ws:
        async for raw in ws:
            item = decode(raw)
            if item is not None:
                history.append(item)
                continue
            # `live`: geçmiş bitti.
            _print(timeline.lines(history))
            if not follow:
                return
            break
        async for raw in ws:
            item = decode(raw)
            if item is not None:
                _print(timeline.lines([item]))


def _print(lines: Iterable[str]) -> None:
    for line in lines:
        print(line, flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mayen-turns")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL)
    parser.add_argument("--since", help="HH:MM today, or an ISO date-time (default: 1 h ago)")
    parser.add_argument("-f", "--follow", action="store_true", help="keep printing live")
    args = parser.parse_args(argv)
    try:
        since = since_of(args.since, datetime.now(UTC))
        asyncio.run(run(args.url, since, args.follow))
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, WebSocketException) as e:
        print(f"[{e}]", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

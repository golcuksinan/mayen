"""Çerçevelerin tele çevrilmesi.

**Kontrol çerçeveleri JSON metin, ses çerçeveleri ikili.** Sesi de JSON'a koymak base64
demektir: her parça %33 şişer ve tur boyunca sürekli kodlanıp çözülür. Her şeyi ikili
yapmak ise protokolü gözle okunamaz hale getirir ve hata ayıklamak için ayrı bir araç
yazmayı gerektirir. İkili çerçeve bu yüzden melez: uzunluk önekli bir JSON başlık +
ham yük. Başlık okunabilir kalır, yük hiç kopyalanmaz.

    [4 bayt başlık uzunluğu, big-endian][JSON başlık][ham yük]

**Bilinmeyen hiçbir şey sessizce geçmez** (Kural 13): tanınmayan tip, eksik alan, fazla
alan, bozuk uzunluk — hepsi `ProtocolError`. Sessizce yok saymak, sürüm uyuşmazlığını
el sıkışmadan kaçırıp turun ortasında gizli davranış farkına çevirirdi.
"""

import json
from dataclasses import fields
from typing import Any

from mayen.adapters.audio import AudioFormat, Codec
from mayen.session.state import State
from mayen.transport.frames import (
    Announcement,
    AudioChunk,
    AudioEnd,
    Cancelled,
    ErrorFrame,
    Frame,
    Hello,
    Interrupt,
    Ping,
    Pong,
    Rejected,
    Reply,
    SpeechSegment,
    StateChanged,
    TextSegment,
    ToolRunning,
    Transcript,
    Welcome,
)

HEADER_LENGTH_BYTES = 4
MAX_HEADER_BYTES = 64 * 1024


class ProtocolError(Exception):
    """Çerçeve okunamadı ya da tanınmadı."""


_FRAME_TYPES: tuple[type[Frame], ...] = (
    Hello,
    SpeechSegment,
    TextSegment,
    Interrupt,
    Ping,
    Welcome,
    Rejected,
    Transcript,
    StateChanged,
    ToolRunning,
    Reply,
    AudioChunk,
    AudioEnd,
    Cancelled,
    ErrorFrame,
    Announcement,
    Pong,
)
_BY_TYPE: dict[str, type[Frame]] = {frame.TYPE: frame for frame in _FRAME_TYPES}

# Yükü tel üzerinde ham taşınan çerçeveler.
_BINARY: tuple[type[Frame], ...] = (SpeechSegment, AudioChunk)


def encode(frame: Frame) -> str | bytes:
    """Metin çerçeve için `str`, ikili çerçeve için `bytes` döner.

    Ayrımı çağıran yapmaz: WebSocket'e hangisi verilirse doğru opcode zaten o olur.
    """
    header = json.dumps(_header(frame), ensure_ascii=False)
    if not isinstance(frame, SpeechSegment | AudioChunk):
        return header
    encoded = header.encode("utf-8")
    return len(encoded).to_bytes(HEADER_LENGTH_BYTES, "big") + encoded + frame.data


def decode(raw: str | bytes) -> Frame:
    if isinstance(raw, str):
        return _from_header(_parse_json(raw), payload=None)
    if len(raw) < HEADER_LENGTH_BYTES:
        raise ProtocolError("İkili çerçeve başlık uzunluğunu taşıyamayacak kadar kısa")
    length = int.from_bytes(raw[:HEADER_LENGTH_BYTES], "big")
    if length > MAX_HEADER_BYTES:
        # Bozuk bir uzunluk, sağlam bir başlıktan ayırt edilemez; sınır olmadan bu bayt
        # dizisi keyfi büyüklükte bir ayırma isteğine dönüşür.
        raise ProtocolError(f"Başlık uzunluğu makul değil: {length}")
    end = HEADER_LENGTH_BYTES + length
    if len(raw) < end:
        raise ProtocolError("İkili çerçeve başlığı eksik")
    header = _parse_json(raw[HEADER_LENGTH_BYTES:end].decode("utf-8"))
    return _from_header(header, payload=raw[end:])


def _parse_json(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ProtocolError(f"Çerçeve JSON değil: {error}") from error
    if not isinstance(parsed, dict):
        raise ProtocolError("Çerçeve bir nesne olmalı")
    return parsed


def _header(frame: Frame) -> dict[str, Any]:
    header: dict[str, Any] = {"type": frame.TYPE}
    for item in fields(frame):
        if item.name == "data":
            continue
        value = getattr(frame, item.name)
        header[item.name] = _to_json(value)
    return header


def _to_json(value: object) -> object:
    if isinstance(value, AudioFormat):
        return {
            "codec": value.codec.value,
            "sample_rate": value.sample_rate,
            "channels": value.channels,
        }
    return value


def _from_header(header: dict[str, Any], *, payload: bytes | None) -> Frame:
    raw_type = header.pop("type", None)
    if not isinstance(raw_type, str):
        raise ProtocolError("Çerçevenin `type` alanı yok")
    frame_type = _BY_TYPE.get(raw_type)
    if frame_type is None:
        raise ProtocolError(f"Tanınmayan çerçeve tipi: {raw_type!r}")

    binary = frame_type in _BINARY
    if binary and payload is None:
        raise ProtocolError(f"{raw_type} ikili çerçeve olarak gelmeliydi")
    if not binary and payload is not None:
        raise ProtocolError(f"{raw_type} metin çerçeve olarak gelmeliydi")

    expected = {item.name for item in fields(frame_type) if item.name != "data"}
    if set(header) != expected:
        missing = sorted(expected - set(header))
        extra = sorted(set(header) - expected)
        raise ProtocolError(f"{raw_type} alanları uyuşmuyor: eksik={missing} fazla={extra}")

    if "format" in header:
        header["format"] = _audio_format(header["format"])
    if frame_type is StateChanged:
        header["state"] = _state(header["state"])
    if payload is not None:
        header["data"] = payload
    try:
        return frame_type(**header)
    except TypeError as error:  # pragma: no cover - alan kümesi yukarıda doğrulandı
        raise ProtocolError(f"{raw_type} kurulamadı: {error}") from error


def _state(value: object) -> State:
    """Tanınmayan durum adı sessizce geçmez (Kural 13): sürüm uyuşmazlığının belirtisidir."""
    try:
        return State(str(value))
    except ValueError as error:
        raise ProtocolError(f"Tanınmayan durum: {value!r}") from error


def _audio_format(value: object) -> AudioFormat:
    if not isinstance(value, dict):
        raise ProtocolError("`format` bir nesne olmalı")
    try:
        codec = Codec(value["codec"])
        return AudioFormat(
            codec=codec, sample_rate=int(value["sample_rate"]), channels=int(value["channels"])
        )
    except (KeyError, ValueError) as error:
        raise ProtocolError(f"`format` okunamadı: {error}") from error

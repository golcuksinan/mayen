"""Süreç montajı: gerçek soket, gerçek veritabanı, gerçek tur koşucusu — sahte LLM.

Testin ölçtüğü şey **kurulumun kendisi**: bir cihazın yolladığı metin segmenti, hiçbir
parça elle bağlanmadan transkripte, sese ve bitişe kadar gidiyor mu. Montajı atlayıp
parçaları testte birleştirmek, tam da bu paketin yazdığı şeyi ölçülmemiş bırakırdı.

LLM sahte, gerisi değil: model üçlüsü seçilmedi (§19.2) ve §4 zaten tüm akışın GPU'suz
koşabilmesini şart koşuyor.
"""

import asyncio
import re
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path

import pytest
from websockets.asyncio.client import ClientConnection, connect

from mayen.adapters.fakes.llm import FakeLLM
from mayen.adapters.fakes.tts import FakeTTS
from mayen.adapters.llm import NativeCall
from mayen.config import Config, ConfigError, ServiceKind
from mayen.data import clock
from mayen.data.db import Database
from mayen.data.repositories.tasks import TaskKind, TaskRepository
from mayen.main import EXIT_CONFIG, App, build, main
from mayen.transport.frames import (
    PROTOCOL_VERSION,
    Announcement,
    AudioChunk,
    AudioEnd,
    Frame,
    Hello,
    Reply,
    TextSegment,
    Transcript,
    Welcome,
)
from mayen.transport.wire import decode, encode

TIMEOUT = 5.0
ANSWER = "It is sunny today. Nothing else to report."

SCHEDULE = """
term = "2026-guz"

[[sessions]]
course_code = "BIL301"
title = "İşletim Sistemleri"
day = 1
start = "09:00"
end = "10:50"
"""


ROLE_PATH = Path(__file__).parent.parent / "config" / "rol.txt"
"""Depoyla gelen gerçek rol dosyası: montaj testi onu da okumuş oluyor."""


def _config(tmp_path: Path, *, courses: bool = True, assume_owner: bool = False) -> Config:
    path = tmp_path / "dersler.toml"
    if courses:
        path.write_text(SCHEDULE, encoding="utf-8")
    return Config(
        db_path=tmp_path / "mayen.db",
        role_path=ROLE_PATH,
        courses_path=path if courses else None,
        host="127.0.0.1",
        port=0,
        assume_owner=assume_owner,
    )


@asynccontextmanager
async def running(config: Config, llm: FakeLLM | None = None) -> AsyncIterator[tuple[int, App]]:
    async with build(
        config, llm=llm if llm is not None else FakeLLM([ANSWER]), tts=FakeTTS()
    ) as app:
        socket = await app.server.serve(config.host, config.port)
        try:
            yield socket.sockets[0].getsockname()[1], app
        finally:
            socket.close()
            await socket.wait_closed()


async def expect[T: Frame](socket: ClientConnection, kind: type[T]) -> T:
    async with asyncio.timeout(TIMEOUT):
        while True:
            frame = decode(await socket.recv())
            if isinstance(frame, kind):
                return frame


async def test_assembled_system_answers_a_text_segment(tmp_path: Path) -> None:
    async with running(_config(tmp_path)) as (port, _):
        socket = await connect(f"ws://127.0.0.1:{port}")
        await socket.send(encode(Hello(protocol_version=PROTOCOL_VERSION, device_id="dev1")))
        assert isinstance(decode(await socket.recv()), Welcome)

        await socket.send(encode(TextSegment(segment_id="s1", text="Hava nasıl?")))
        transcript = await expect(socket, Transcript)
        assert transcript.text == "Hava nasıl?"
        chunk = await expect(socket, AudioChunk)
        assert chunk.turn_id == transcript.turn_id
        assert chunk.seq == 0
        await expect(socket, AudioEnd)
        await socket.close()


CALL = ["", "It is late."]
"""Üretimin çağrı biçimi **yerel** (`main.CALL_FORMAT`): çağrı modelin metninde değil,
`tool_calls` alanında. Metin sırası bu yüzden boş bir ilk üretim ve ardından cevap;
çağrının kendisi `_calling()` ile sıraya konuyor."""


def _calling(*, tool: str = "date_time") -> FakeLLM:
    llm = FakeLLM(CALL)
    llm.queue_native(NativeCall(name=tool, arguments={}))
    return llm


async def _ask(port: int, text: str) -> None:
    socket = await connect(f"ws://127.0.0.1:{port}")
    await socket.send(encode(Hello(protocol_version=PROTOCOL_VERSION, device_id="dev1")))
    assert isinstance(decode(await socket.recv()), Welcome)
    await socket.send(encode(TextSegment(segment_id="s1", text=text)))
    await expect(socket, AudioEnd)
    await socket.close()


def _tool_feedback(llm: FakeLLM) -> str:
    """Modele tool sonucu olarak ne döndüğü. Yetki kararı `ToolRunning` çerçevesinden
    okunamaz: o çerçeve §6 gereği çağrı **çalışmadan önce** gidiyor."""
    return "\n".join(
        message.content for call in llm.calls for message in call if message.role == "tool"
    )


async def test_without_the_owner_flag_no_tool_runs(tmp_path: Path) -> None:
    # §19.3 açık olduğu için kimlik TANINMAYAN; §10.2'nin o satırında dört hücre de RED.
    # Red bir istisna değil, modele geri beslenen sonuç (§8.2) — yani sessiz de değil.
    llm = _calling()
    async with running(_config(tmp_path), llm) as (port, _):
        await _ask(port, "Saat kaç?")
    assert "yetki yok" in _tool_feedback(llm)


async def test_the_owner_flag_lets_a_tool_run(tmp_path: Path) -> None:
    # MAYEN_ASSUME_OWNER: gömüye bakılmadan SAHİP. Kapı ses değil kabuk, Kural 6 duruyor.
    llm = _calling()
    async with running(_config(tmp_path, assume_owner=True), llm) as (port, _):
        await _ask(port, "Saat kaç?")
    assert "yetki yok" not in _tool_feedback(llm)


SPOKEN = "I am reminding you to take your medicine."
"""Bildirimde **söylenen** cümle: notun kendisi değil, modelin onun üzerine kurduğu söz."""


async def test_a_due_reminder_reaches_the_connected_client(tmp_path: Path) -> None:
    """§12'nin proaktif kanalı, montajın kurduğu gerçek sistemde: kullanıcı hiçbir şey
    sormuyor ve ses yine de geliyor — kendi `turn_id`'siyle, onu açan çerçeveyle."""
    async with running(_config(tmp_path), FakeLLM([SPOKEN])) as (port, app):
        socket = await connect(f"ws://127.0.0.1:{port}")
        await socket.send(encode(Hello(protocol_version=PROTOCOL_VERSION, device_id="dev1")))
        assert isinstance(decode(await socket.recv()), Welcome)

        TaskRepository(app.database).create(
            TaskKind.REMINDER.value, {"message": "Time for your medicine."}, clock.now()
        )
        await app.scheduler.tick()

        notice = await expect(socket, Announcement)
        # Duyulan şey kullanıcının notu değil, asistanın cümlesi (`scheduler/phrasing.py`).
        assert notice.text == SPOKEN
        chunk = await expect(socket, AudioChunk)
        assert chunk.turn_id == notice.turn_id
        await expect(socket, AudioEnd)
        await socket.close()


async def test_a_reminder_with_nobody_connected_waits_for_the_first_device(
    tmp_path: Path,
) -> None:
    async with running(_config(tmp_path), FakeLLM([SPOKEN])) as (port, app):
        TaskRepository(app.database).create(
            TaskKind.REMINDER.value, {"message": "Time for your medicine."}, clock.now()
        )
        await app.scheduler.tick()

        socket = await connect(f"ws://127.0.0.1:{port}")
        await socket.send(encode(Hello(protocol_version=PROTOCOL_VERSION, device_id="dev1")))
        assert isinstance(decode(await socket.recv()), Welcome)

        notice = await expect(socket, Announcement)
        assert notice.text == SPOKEN
        await socket.close()


async def test_schedule_is_loaded_at_startup(tmp_path: Path) -> None:
    config = _config(tmp_path)
    async with build(config, llm=FakeLLM(), tts=FakeTTS()) as app:
        assert app.course_term == "2026-guz"


async def test_without_a_schedule_file_the_term_is_empty(tmp_path: Path) -> None:
    """Dosya verilmemesi bir hata değil — ama dönem uydurulmuyor da."""
    async with build(_config(tmp_path, courses=False), llm=FakeLLM(), tts=FakeTTS()) as app:
        assert app.course_term == ""


async def test_real_stt_stops_the_process_instead_of_falling_back(tmp_path: Path) -> None:
    """§19.2'nin STT yarısı açık: `real` seçilebilir bir şey değil.

    Sessizce sahteye düşmek, açık bir maddeyi varsayımla kapatmak olurdu — üstelik
    kullanıcı gerçek STT ile koştuğunu sanarak. Hata kalıcı sınıfta, yani EXIT_CONFIG.
    """
    config = replace(_config(tmp_path), stt=ServiceKind.REAL)
    with pytest.raises(ConfigError, match=re.escape("§19.2")):
        async with build(config, llm=FakeLLM()):
            pass


async def test_fake_tts_is_chosen_from_the_configuration(tmp_path: Path) -> None:
    """Kokoro servisi kapalıyken uçtan uca konuşabilmek: bayrak montajda karşılığını
    buluyor, hiçbir üst katman biçimi görmüyor."""
    config = replace(_config(tmp_path), tts=ServiceKind.FAKE)
    async with build(config, llm=FakeLLM([ANSWER])) as app:
        assert app.tts.name == "fake-tts"


async def test_build_closes_what_it_opened(tmp_path: Path) -> None:
    async with build(_config(tmp_path), llm=FakeLLM(), tts=FakeTTS()) as app:
        pass
    assert app.http.is_closed
    with pytest.raises(sqlite3.ProgrammingError), app.database.transaction():
        pass


def test_broken_configuration_exits_with_the_permanent_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kalıcı hata yeniden başlatılmamalı: birim dosyası bu kodda durur. Aynı kodu 1
    döndürseydik servis hatayı sonsuz bir döngünün içine gömer ve kimse görmezdi."""
    monkeypatch.setenv("MAYEN_DB_PATH", str(tmp_path / "mayen.db"))
    monkeypatch.setenv("MAYEN_ROLE_PATH", str(tmp_path / "olmayan-rol.txt"))
    assert main([]) == EXIT_CONFIG


def test_a_second_instance_exits_with_the_permanent_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Servis koşarken elle başlatılan ikinci süreç (Kural 1). Yeniden başlatmak
    düzeltmez — ilk süreç kapanana kadar hep aynı hata."""
    path = tmp_path / "mayen.db"
    role = tmp_path / "rol.txt"
    role.write_text("Sen Mayen'sin.", encoding="utf-8")
    monkeypatch.setenv("MAYEN_DB_PATH", str(path))
    monkeypatch.setenv("MAYEN_ROLE_PATH", str(role))
    with Database(path):
        assert main([]) == EXIT_CONFIG


async def test_the_answer_text_reaches_the_client_as_its_own_frame(tmp_path: Path) -> None:
    """Cevabın metni sesin yanında gidiyor (§13'ün `Reply`'ı).

    Gerçek TTS'te yük ham PCM: metin ayrı bir çerçeveyle gitmezse kullanıcı kendi
    sorusunu görüp cevabı hiç göremez. Faz 7'de tam olarak bu oldu.
    """
    async with running(_config(tmp_path)) as (port, _):
        socket = await connect(f"ws://127.0.0.1:{port}")
        await socket.send(encode(Hello(protocol_version=PROTOCOL_VERSION, device_id="dev1")))
        assert isinstance(decode(await socket.recv()), Welcome)

        await socket.send(encode(TextSegment(segment_id="s1", text="Hava nasıl?")))
        transcript = await expect(socket, Transcript)
        reply = await expect(socket, Reply)
        assert reply.turn_id == transcript.turn_id
        assert reply.text in ANSWER
        await expect(socket, AudioEnd)
        await socket.close()

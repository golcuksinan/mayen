"""Kayıt yapılandırması kurulabiliyor ve bağlam alanları çıktıya giriyor."""

import json
import logging

import structlog

from mayen.obs.log import configure, get_logger


def test_context_fields_reach_output() -> None:
    configure(level=logging.INFO, json=True)
    with structlog.testing.capture_logs() as records:
        get_logger(__name__).info("tur_basladi", turn_id="t-1")

    assert records == [{"event": "tur_basladi", "turn_id": "t-1", "log_level": "info"}]


def test_json_renderer_emits_valid_json(capsys: object) -> None:
    configure(level=logging.INFO, json=True)
    get_logger(__name__).info("tur_bitti", turn_id="t-1")
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    line = json.loads(captured.out)
    assert line["event"] == "tur_bitti"
    assert line["turn_id"] == "t-1"
    assert line["timestamp"].endswith("Z")

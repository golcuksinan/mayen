"""Model servislerinin sözleşmesi (§3, §4): çekirdekle STT, TTS ve konuşmacı süreçleri
arasındaki HTTP.

Servisler ayrı projelerdir ve bu modülü import etmez; tanımı kendi kodlarında aynen kurar.
Her yanıt `schema_version` taşır; tutmayan yanıt kullanılmaz (§18).

STT: `POST /transcribe?language=<kod>` gövdesi ham PCM (16 bit, tek kanal, `sample_rate`
hızında); yanıt JSON: `text`, `language` ve Whisper'ın kendi kuralından geçen parçalar.
Dil verilmezse model kendisi bulur.

VAD: `WS /vad`. Servis bağlanınca bir JSON selam yollar (`schema_version`, `sample_rate`,
`frame`); istemci ardından `frame` örneklik ham PCM parçaları gönderir, servis her parçaya
sırasıyla bir konuşma olasılığıyla (4 bayt, float32, little-endian) cevap verir. Model durumu
bağlantı başınadır: bir bağlantı tek bir ses akışıdır. Olasılığı söze çeviren kural (eşik,
başlama ve bitiş süreleri) çekirdektedir; serviste yalnızca model durur.

Sözün bitişi: `POST /turn?sample_rate=<hız>` gövdesi bir sözün o ana kadarki sesi, ham PCM
(16 bit, tek kanal); yanıt JSON: `probability`, sözün bittiği olasılığı. Hız servisinkini
tutmazsa servis 400 döner. Olasılığı karara çeviren eşik çekirdektedir.

Wake word: `WS /wake`, `/vad` gibi: selam (`schema_version`, `sample_rate`, `frame`), sonra her
`frame` örneklik parçaya sırasıyla bir puan (4 bayt, float32): bu parçayla biten sesin wake
word olduğu olasılığı. Durum bağlantı başınadır. Serviste wake word modeli yoksa selamdan önce
1011 koduyla kapanır. Eşik çekirdektedir.

TTS: `POST /speak` gövdesi JSON: `voice` ve sırasıyla okunacak `parts`; her parçanın
`language`'ı `null` ise sesin kendi dilidir, değilse parça o dilin okunuşuyla aynı sese
verilir (§7). Yanıt `sample_rate` hızında ham PCM akışıdır; ilk ses üretilir üretilmez gelir.
Ses biriminin zamanını bilen ses, yanıtın `X-Word-Ends` başlığında sesin kelime gruplarının
bitişlerini verir (saniye, sesin başından, virgülle). Gruplar metnin kelimeleriyle birebir
değildir (okunuş kısa kelimeleri birleştirir); başlık isteğe bağlıdır, yoksa cümle bitince
bütün söylenmiş sayılır.

Konuşmacı (§6, §10.5): ayrı bir servis. `POST /embed` gövdesi bir sözün sesi, ham PCM (16 bit,
tek kanal, `sample_rate` hızında); yanıt JSON: `model` ve `vector`, sesin izi (birim uzunlukta).
Servis kimseyi tanımaz, iz tutmaz: izi kayıtlı izlerle karşılaştırıp puanı bulan ve eşikle
karar veren çekirdektir. `model` izin hangi modelle çıkarıldığıdır; başka modelin iziyle
karşılaştırılmaz.

Hepsi `GET /health` ile biçimini bildirir. Çıkış biçimi sabittir; bildirilen biçim
bekleneni tutmazsa istemci yüksek sesle başarısız olur (§14).
"""

import re
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = 1

HEALTH = "/health"
TRANSCRIBE = "/transcribe"
SPEAK = "/speak"
WORD_ENDS = "X-Word-Ends"
VAD = "/vad"
TURN = "/turn"
WAKE = "/wake"
EMBED = "/embed"

VAD_FRAME = 512
"""VAD modelinin bir seferde baktığı örnek sayısı (16 kHz'de 32 ms): modelin özelliği."""

WAKE_FRAME = 1280
"""Wake word modelinin bir adımı (16 kHz'de 80 ms): modelin özelliği."""


class SpeechContractError(Exception):
    """Servisin yanıtı sözleşmeyi tutmuyor: sürüm, alan ya da biçim."""


@dataclass(frozen=True)
class Health:
    sample_rate: int
    voices: tuple[str, ...]  # STT'de boş


@dataclass(frozen=True)
class Segment:
    text: str
    no_speech_prob: float
    avg_logprob: float


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str
    segments: tuple[Segment, ...]


@dataclass(frozen=True)
class Embedding:
    """Bir sözün ses izi; `model` onu çıkaran modelin adıdır."""

    model: str
    vector: tuple[float, ...]


@dataclass(frozen=True)
class Part:
    """Okunacak metnin bir parçası; `language` yoksa sesin kendi dili (§7)."""

    language: str | None
    text: str


TAG = re.compile(r"<(/?)([a-z]{2})>")
"""Modelin metne koyduğu dil işareti (`<tr>…</tr>`, §7)."""


def untagged(text: str) -> str:
    """Gösterilen metin: işaret seslendirilmediği gibi görünmez de (§7)."""
    return TAG.sub("", text)


def _versioned(body: Any) -> dict[str, Any]:  # noqa: ANN401  # çözülmüş JSON
    if not isinstance(body, dict):
        raise SpeechContractError("response is not an object")
    if body.get("schema_version") != SCHEMA_VERSION:
        raise SpeechContractError(
            f"schema_version {body.get('schema_version')!r}, expected {SCHEMA_VERSION}"
        )
    return body


def parse_health(body: Any) -> Health:  # noqa: ANN401
    b = _versioned(body)
    try:
        return Health(int(b["sample_rate"]), tuple(str(v) for v in b.get("voices", [])))
    except (KeyError, TypeError, ValueError) as e:
        raise SpeechContractError(f"health: {e}") from e


def parse_transcription(body: Any) -> Transcription:  # noqa: ANN401
    b = _versioned(body)
    try:
        return Transcription(
            str(b["text"]),
            str(b["language"]),
            tuple(
                Segment(str(s["text"]), float(s["no_speech_prob"]), float(s["avg_logprob"]))
                for s in b["segments"]
            ),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise SpeechContractError(f"transcription: {e}") from e


def parse_embedding(body: Any) -> Embedding:  # noqa: ANN401
    b = _versioned(body)
    try:
        vector = tuple(float(x) for x in b["vector"])
        if not vector:
            raise ValueError("empty vector")
        return Embedding(str(b["model"]), vector)
    except (KeyError, TypeError, ValueError) as e:
        raise SpeechContractError(f"embedding: {e}") from e


@dataclass(frozen=True)
class StreamHello:
    """Akış uçlarının (`/vad`, `/wake`) selamı: servisin hızı ve parça boyu."""

    sample_rate: int
    frame: int


def parse_stream_hello(body: Any, endpoint: str) -> StreamHello:  # noqa: ANN401
    b = _versioned(body)
    try:
        return StreamHello(int(b["sample_rate"]), int(b["frame"]))
    except (KeyError, TypeError, ValueError) as e:
        raise SpeechContractError(f"{endpoint}: {e}") from e


def parse_turn(body: Any) -> float:  # noqa: ANN401
    """Sözün bittiği olasılığı."""
    b = _versioned(body)
    try:
        return float(b["probability"])
    except (KeyError, TypeError, ValueError) as e:
        raise SpeechContractError(f"turn: {e}") from e


def speak_request(voice: str, parts: list[Part]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "voice": voice,
        "parts": [{"language": p.language, "text": p.text} for p in parts],
    }

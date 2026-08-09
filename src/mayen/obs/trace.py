"""Tur izi: kimlik üretimi, aşama ölçümü, kalıcı yazım sözleşmesi (§15).

**Bağımlılık burada tersine dönüyor.** §4'e göre `obs` en dipte ve `data`'yı import edemez;
ama iz kalıcı yazılmak zorunda. Çözüm import eklemek değil (sınır testi zaten reddederdi):
`obs` bir `TraceSink` `Protocol`'ü tanımlar, `data.repositories.traces.TraceRepository`
onu uygular. Dokümanın LLM/STT/TTS için kullandığı ports & adapters kalıbının aynısı.

**İz gövde kopyalamaz.** Mesajın kendisi `messages` tablosunda durur; iz yalnızca
`turn_id` ile ona referans verir, aşama satırında da en fazla kısa bir `detail` taşır.
Kopyalamak §15'in kayıt hacmi kuralıyla çakışır ve her turun tam metnini iki kere yazar.
"""

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from enum import StrEnum
from types import TracebackType
from typing import Protocol, Self


class Stage(StrEnum):
    """§15'in saydığı aşamalar.

    Tool aşamaları burada değil: adları çalışma anında belli olur ve `tool_stage()` ile
    üretilir. Şemadaki `name` de bu yüzden sabit bir kümeye bağlanmadı.
    """

    KONUSMACI = "konusmaci"
    STT = "stt"
    BAGLAM = "baglam"
    LLM_ILK_TOKEN = "llm_ilk_token"
    LLM_TOPLAM = "llm_toplam"
    TTS_ILK_PARCA = "tts_ilk_parca"
    ILK_SES = "ilk_ses"


class Outcome(StrEnum):
    """Turun nasıl bittiği. `IPTAL` bir hata değil, beklenen bir son (Kural 12)."""

    TAMAM = "tamam"
    IPTAL = "iptal"
    HATA = "hata"


def tool_stage(tool_name: str) -> str:
    """Tool aşamasının adı. Tek yerde üretiliyor ki `tool:` öneki iki modülde iki türlü
    yazılmasın — sonradan izleri ada göre süzmek imkânsız hale gelirdi."""
    return f"tool:{tool_name}"


def new_turn_id() -> str:
    """Yeni tur kimliği.

    §13 gereği bu kimlik tel formatının parçası: her ses parçası onu taşır ve istemci
    aktif `turn_id` dışındaki parçaları atar. Bu yüzden çakışmaması bir kolaylık değil,
    doğruluk şartı — sayaç değil, uuid.
    """
    return uuid.uuid4().hex


class TraceSink(Protocol):
    """İzin yazıldığı yer. `data` bunu uygular; `obs` onu tanımaz."""

    def start(self, turn_id: str, device_id: str, *, person_id: int | None = None) -> None: ...

    def add_stage(
        self,
        turn_id: str,
        name: str,
        *,
        duration_ms: int | None = None,
        detail: str | None = None,
    ) -> None: ...

    def finish(self, turn_id: str, outcome: str) -> None: ...


class TurnTrace:
    """Tek turun izi. Aşama süreleri `monotonic` saatle ölçülür.

    Duvar saatiyle ölçmek yanlış olurdu: sistem saati tur ortasında geri alınırsa negatif
    süre yazılır ve ölçüm sessizce bozulur. Aşamanın *ne zaman* başladığı ayrı bir şey ve
    onu `data/clock.py` yazıyor.
    """

    def __init__(
        self,
        sink: TraceSink,
        device_id: str,
        *,
        turn_id: str | None = None,
        person_id: int | None = None,
    ) -> None:
        self.turn_id = turn_id if turn_id is not None else new_turn_id()
        self._sink = sink
        self._device_id = device_id
        self._person_id = person_id
        self._finished = False

    def __enter__(self) -> Self:
        self._sink.start(self.turn_id, self._device_id, person_id=self._person_id)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Sonuç açıkça verilmediyse istisnadan türetilir.

        Kural 13: yarım kalmış bir iz "bitmemiş tur"dan ayırt edilemez. `finish` çağrısını
        unutan bir yol, izi sessizce `ended_at IS NULL` bırakırdı."""
        if self._finished:
            return
        if exc_type is None:
            self.finish(Outcome.TAMAM)
        elif issubclass(exc_type, Exception):
            self.finish(Outcome.HATA)
        else:
            self.finish(Outcome.IPTAL)

    @contextmanager
    def stage(self, name: str, *, detail: str | None = None) -> Iterator[None]:
        """Aşamayı ölçer ve **her durumda** yazar — istisna çıksa da.

        Yalnızca başarılı aşamaları yazmak, ölçümün en çok işe yaradığı anı (bir şeyin
        yavaşlayıp patladığı anı) kayıttan silerdi.
        """
        started = time.monotonic()
        try:
            yield
        finally:
            elapsed_ms = round((time.monotonic() - started) * 1000)
            self._sink.add_stage(self.turn_id, name, duration_ms=elapsed_ms, detail=detail)

    def mark(self, name: str, *, detail: str | None = None) -> None:
        """Süresi olmayan aşama — "ilk token geldi" gibi bir an."""
        self._sink.add_stage(self.turn_id, name, detail=detail)

    def finish(self, outcome: Outcome) -> None:
        self._finished = True
        self._sink.finish(self.turn_id, outcome)

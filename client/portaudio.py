"""`AudioSource`/`AudioPlayer`'ın PortAudio (`sounddevice`) uygulaması.

Ayrı bir modül, çünkü `client/audio.py` bağımlılıksız kalmalı: metin istemcisi ses kartı
olmayan bir makinede de koşuyor ve testler sahtelerle çalışıyor. `sounddevice` import'u bu
yüzden fonksiyonun içinde; kurulu değilse mesaj kurulum talimatı veriyor.

**Mikrofon geri çağrımı ayrı bir iş parçacığında koşuyor** (PortAudio öyle çağırıyor):
çerçeve olay döngüsüne `call_soon_threadsafe` ile geçiyor. Kuyruk sınırlı ve **dolduğunda
en eski çerçeve düşüyor** — gidenin ne olduğu sayılıyor. Bloklamak, ses kartının geri
çağrımını bekletmek demek; PortAudio'da bunun karşılığı tıklama ve altakış.

**`stop()` `abort()` kullanıyor, `stop()` değil:** PortAudio'nun `stop()`'u tampondakini
çalıp bitiriyor, `abort()` atıyor. Söz kesmede kullanıcı asistanın yarım cümlesini duymayı
bırakmak istiyor — yarım saniye daha dinlemeyi değil.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator, Buffer
from types import ModuleType
from typing import Any

from client.audio import FORMAT, FRAME_BYTES, SAMPLE_BYTES

QUEUE_FRAMES = 50
"""Bir saniyelik mikrofon tamponu (20 ms'lik çerçevelerle). Daha büyüğü, tıkanan bir
istemcinin saniyeler önceki sesi tur açması demek olurdu."""


class MissingBackendError(Exception):
    """`sounddevice` kurulu değil. Sessizce sessiz mikrofona düşülmüyor (Kural 13)."""


def _sounddevice() -> ModuleType:
    try:
        import sounddevice
    except OSError as error:  # PortAudio sistem kütüphanesi yok
        raise MissingBackendError(f"PortAudio bulunamadı: {error}") from error
    except ImportError as error:
        raise MissingBackendError(
            "sounddevice kurulu değil: `uv sync --extra voice` (PortAudio da gerekir)"
        ) from error
    module: ModuleType = sounddevice
    return module


def ensure_backend() -> None:
    """Arka ucu bağlanmadan önce yoklar; eksikse anlaşılır bir hata verir."""
    _sounddevice()


class Microphone:
    """PortAudio girişi. `frames()` çağrıldığında akış açılır, çıkışta kapanır."""

    def __init__(self, *, device: int | str | None = None) -> None:
        self._device = device
        self.dropped = 0

    async def frames(self) -> AsyncIterator[bytes]:
        sd = _sounddevice()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=QUEUE_FRAMES)

        def deliver(frame: bytes) -> None:
            try:
                queue.put_nowait(frame)
            except asyncio.QueueFull:
                # En eskiyi atıyoruz: gecikmiş ses, kaybolan sesten kötü.
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
                self.dropped += 1
                queue.put_nowait(frame)

        def callback(data: Buffer, frames: int, time: object, status: object) -> None:
            loop.call_soon_threadsafe(deliver, bytes(data))

        stream = sd.RawInputStream(
            samplerate=FORMAT.sample_rate,
            blocksize=FRAME_BYTES // 2,
            dtype="int16",
            channels=FORMAT.channels,
            device=self._device,
            callback=callback,
        )
        stream.start()
        try:
            while True:
                yield await queue.get()
        finally:
            stream.stop()
            stream.close()


class Speaker:
    """PortAudio çıkışı. Yazma bloklayan bir çağrı, o yüzden ayrı iş parçacığında."""

    def __init__(self, *, device: int | str | None = None) -> None:
        self._device = device
        self._stream: Any | None = None
        self._tail = b""
        """Yarım kalan örnek. Bkz. `play()`."""

    # `sounddevice` tip bilgisi yollamıyor; akış nesnesinin tipi `Any` olmak zorunda.
    def _open(self) -> Any:  # noqa: ANN401
        if self._stream is None:
            sd = _sounddevice()
            self._stream = sd.RawOutputStream(
                samplerate=FORMAT.sample_rate,
                dtype="int16",
                channels=FORMAT.channels,
                device=self._device,
            )
            self._stream.start()
        return self._stream

    async def play(self, data: bytes) -> None:
        """Parçayı çalar; **örnek sınırında olmayan artığı bir sonraki parçaya taşır**.

        Çerçeve sınırı örnek sınırı değil: servis ffmpeg'in çıktısını sabit boyutta okuyor
        ve dönen parçanın uzunluğu tek olabilir. PortAudio bunu `ValueError` ile reddediyor
        ve hata, sesi cümlenin ortasında kesiyordu. Artığı atmak da olmazdı — kalan bayt
        sonraki parçanın ilk baytının yarısı; atılırsa akış bir bayt kayar ve o noktadan
        sonra bütün ses gürültüye döner.
        """
        stream = self._open()
        data = self._tail + data
        cut = len(data) - len(data) % SAMPLE_BYTES
        self._tail = data[cut:]
        if cut:
            await asyncio.to_thread(stream.write, data[:cut])

    async def stop(self) -> None:
        """Tampondakini **atar** (bkz. modül başlığı) ve akışı yeniden başlatır."""
        if self._stream is None:
            return
        # Artık da atılıyor: sonraki cevabın ilk baytıyla birleşseydi onu kaydırırdı.
        self._tail = b""
        self._stream.abort()
        self._stream.start()

    async def close(self) -> None:
        self._tail = b""
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None

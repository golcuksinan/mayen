"""`TTSClient`'ın Kokoro uygulaması (§3, §14).

Servis kendi sürecinde koşuyor (`services/kokoro/`); burası yalnızca onun HTTP yüzü.
Kural 2 gereği bu dosyada model yok, `torch` yok, ses işleme yok — biçim dönüştürme ve
efekt zinciri servisin tarafında, ffmpeg'de.

**Biçim burada bir sabit, servise sorulmuyor.** `output_format` senkron bir özellik ve
her cümle için bir HTTP isteği daha atmak, seslendirmenin önüne ölçülmemiş bir gecikme
koymak olurdu. Sabitin karşılığı servis tarafında da sabit (`OUTPUT_RATE`, ayarlanabilir
değil) ve ikisinin ayrışması **sessiz kalmıyor**: `health()` servisin bildirdiği biçime
bakıyor, uymuyorsa hem `False` dönüyor hem sebebi yazıyor (Kural 13). Ayrışmanın sesteki
karşılığı "tiz/pes konuşan asistan"dır; teşhisi kayda düşmesi gerekir.

**Akış yeniden denenmiyor.** `llamacpp`'deki gerekçenin aynısı: yarısı oynatılmış bir
cümlenin tekrarı, kullanıcının aynı sözü iki kez duyması demek. İptal de aynı yoldan —
üreteci kapatmak HTTP yanıtını kapatır, servis de akışını yarıda bırakır (Kural 12).
"""

from collections.abc import AsyncGenerator

import httpx

from mayen.adapters.audio import AudioFormat, Codec
from mayen.adapters.errors import ServiceFailedError, ServiceUnavailableError
from mayen.obs.log import get_logger

log = get_logger(__name__)

OUTPUT_FORMAT = AudioFormat(codec=Codec.PCM16, sample_rate=16_000, channels=1)
"""Servisin ürettiği biçim. `client/audio.py`'nin `FORMAT`'ı ile aynı sayı: yerelde tek
bir ses biçimi var, mikrofon da hoparlör de o hızda."""


class KokoroTTS:
    """Kokoro servisi arkasındaki TTS.

    İstemci dışarıdan veriliyor (`LlamaCppLLM` ile aynı gerekçe): zaman aşımı ve bağlantı
    havuzu çağıranın elinde kalsın, test gerçek ağa çıkmadan taşımayı değiştirebilsin diye.
    """

    def __init__(self, http: httpx.AsyncClient, *, name: str = "kokoro") -> None:
        self._http = http
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def output_format(self) -> AudioFormat:
        return OUTPUT_FORMAT

    async def health(self) -> bool:
        """§14: yokluk normal bir cevap, istisna değil. Biçim uyuşmazlığı da sağlıksızlık
        sayılıyor — çalışan ama yanlış hızda ses üreten bir servis, çalışıyor değildir."""
        try:
            response = await self._http.get("/health")
        except httpx.HTTPError:
            return False
        if response.status_code != httpx.codes.OK:
            return False
        try:
            payload = response.json()
        except ValueError:
            return False
        if not isinstance(payload, dict) or not payload.get("ok"):
            return False
        return self._matches(payload)

    def _matches(self, payload: dict[str, object]) -> bool:
        reported = (
            payload.get("codec"),
            payload.get("sample_rate"),
            payload.get("channels"),
        )
        expected = (
            OUTPUT_FORMAT.codec.value,
            OUTPUT_FORMAT.sample_rate,
            OUTPUT_FORMAT.channels,
        )
        if reported != expected:
            log.error(
                "TTS servisi beklenenden başka bir biçim bildiriyor",
                service=self._name,
                expected=expected,
                reported=reported,
            )
            return False
        return True

    async def synthesize(self, text: str) -> AsyncGenerator[bytes]:
        """Metni servise verir ve gelen PCM parçalarını olduğu gibi akıtır."""
        try:
            async with self._http.stream(
                "POST", "/synthesize", json={"text": text}
            ) as response:
                if response.status_code != httpx.codes.OK:
                    await response.aread()
                    raise ServiceFailedError(
                        self._name,
                        f"/synthesize {response.status_code} döndü: {response.text[:200]}",
                    )
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError(self._name, f"akış kesildi: {exc}") from exc

"""Her model servisinin ortak yüzü.

§14: her model servisinin bir sağlık kontrolü vardır ve core servisleri düzenli yoklar.
Yoklayıcının dört ayrı tip tanıması gerekmesin diye ortak taban burada; dördü de bunu
genişletir.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ModelService(Protocol):
    """Kendi sürecinde, HTTP arkasında yaşayan bir model (Kural 2, §3)."""

    @property
    def name(self) -> str:
        """Kayıtta ve kullanıcıya gösterilen ad."""
        ...

    async def health(self) -> bool:
        """Servis istek alabilir durumda mı. Hata fırlatmaz — yokluk normal bir cevaptır
        (§14, kısmi çalışma)."""
        ...

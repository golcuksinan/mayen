"""Adaptör hataları.

§14: bir model servisi yanıt vermezse kısmi çalışma açıkça desteklenir — LLM ayakta ama
TTS yoksa yanıt metin olarak gösterilir. Bunun mümkün olması için "servis yok" ile
"servis hata döndürdü" ayrı tiplerdir; üst katman ikisine aynı tepkiyi veremez.

Kural 13 gereği hiçbiri sessizce yutulmaz: yakalayan katman ya kullanıcıya ya kayda
yansıtır.
"""


class AdapterError(Exception):
    """Bir model servisiyle konuşurken oluşan her hatanın tabanı."""

    def __init__(self, service: str, message: str) -> None:
        super().__init__(f"{service}: {message}")
        self.service = service


class ServiceUnavailableError(AdapterError):
    """Servise ulaşılamadı ya da sağlık kontrolünden geçmedi. Yeniden başlatma ve geri
    çekilmeli yeniden deneme bu hataya bağlanır (§14)."""


class ServiceFailedError(AdapterError):
    """Servis ayakta ve yanıt verdi, ama istek başarısız oldu. Yeniden başlatmak bunu
    düzeltmez; hata yukarı taşınır."""

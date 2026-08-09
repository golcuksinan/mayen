"""Sürümlü el sıkışma (§13).

Uyuşmazlıkta bağlantı **açık bir hatayla** reddedilir. Sessizce farklı davranmak en pahalı
seçenek: hata, protokolün değiştiği anda değil, aylar sonra anlaşılmayan bir çerçevede
ortaya çıkar.
"""

from mayen.transport.frames import PROTOCOL_VERSION, Frame, Hello, Rejected, Welcome


def negotiate(frame: Frame) -> Welcome | Rejected:
    """Bağlantının ilk çerçevesine verilen cevap.

    İstisna değil çerçeve döndürüyor, çünkü ret de protokolün bir parçası: istemcinin
    sunucunun sürümünü öğrenip nedenini gösterebilmesi gerekiyor. `Rejected` gönderildikten
    sonra bağlantı kapatılır.
    """
    if not isinstance(frame, Hello):
        return Rejected(
            reason=f"İlk çerçeve el sıkışma olmalı, {frame.TYPE!r} geldi",
            server_version=PROTOCOL_VERSION,
        )
    if frame.protocol_version != PROTOCOL_VERSION:
        return Rejected(
            reason=(
                f"Protokol sürümü uyuşmuyor: istemci {frame.protocol_version}, "
                f"sunucu {PROTOCOL_VERSION}"
            ),
            server_version=PROTOCOL_VERSION,
        )
    return Welcome(protocol_version=PROTOCOL_VERSION)

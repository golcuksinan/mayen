"""Tipli çerçeveler (§13).

**Yön asimetriktir ve bu bilinçlidir.** Sunucudan giden ses parçalıdır ve `(turn_id, seq)`
taşır (§13): iptal bildirimi gittikten sonra ağda ve istemci tamponunda ölü turun
parçaları kalır, `seq` tek başına onları yeni turun ilk parçasından ayıramaz. İstemciden
gelen ses ise **tamamlanmış bir segmenttir** — endpointing istemcide çalışır (§7), sunucu
tekrar tespit yapmaz. Segment henüz bir tura ait değil; `turn_id`'yi sunucu segmenti
alınca üretir. Bu yüzden gelen çerçeve `segment_id` taşır ve sunucu `Transcript` ile
ikisini birbirine bağlar.

**Metin segmenti sesin yanında birinci sınıf bir çerçevedir** (P1). Sahte STT istemcinin
metnini transkript sayıyor; o yol protokolde yoksa gerçek STT geldiğinde protokol
yeniden açılır.

**Cevabın metni de öyle** (`Reply`, Faz 7). Sahte TTS'in yükü okunabilir metin olduğu için
istemciler cevabı ses parçalarını UTF-8 çözerek gösteriyordu; Kokoro bağlanınca o yol
kapandı ve kullanıcı kendi sorusunu görüp cevabı göremez oldu. Metin sesin yanında ayrı
bir çerçeve olarak gidiyor — `Transcript`'in kullanıcı için yaptığının aynısı. Sesin
*yerine* değil: ikisi de aynı `turn_id`'yi taşıyor ve metin, ait olduğu cümlenin sesinden
**önce** yazılıyor.
"""

from dataclasses import dataclass, field
from typing import ClassVar

from mayen.adapters.audio import AudioFormat
from mayen.session.state import State

# Sürüm çerçeve biçimi her değiştiğinde artar. El sıkışmada karşılaştırılır ve
# uyuşmazlık açık bir hatayla reddedilir — sessizce farklı davranılmaz (§13).
PROTOCOL_VERSION = 2
"""2: `Reply` eklendi (Faz 7). Eski bir istemci cevabın metnini hiç görmezdi, yani
uyuşmazlık sessizce yaşanabilecek bir fark değil — el sıkışma onu reddediyor."""


# --- istemci → sunucu ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Hello:
    """El sıkışma. Bağlantının ilk çerçevesi."""

    TYPE: ClassVar[str] = "hello"

    protocol_version: int
    device_id: str


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    """Tamamlanmış konuşma segmenti (§7). İkili çerçeve."""

    TYPE: ClassVar[str] = "speech_segment"

    segment_id: str
    format: AudioFormat
    data: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class TextSegment:
    """Yazıyla gelen segment. Sahte STT'nin ve başsız istemcinin yolu (P1)."""

    TYPE: ClassVar[str] = "text_segment"

    segment_id: str
    text: str


@dataclass(frozen=True, slots=True)
class Interrupt:
    """Söz kesme. Kapsamı **tek tur**, kuyruğun tamamı değil (§12): kuyruktaki proaktif
    hatırlatıcı bundan etkilenmez."""

    TYPE: ClassVar[str] = "interrupt"

    turn_id: str


@dataclass(frozen=True, slots=True)
class Ping:
    TYPE: ClassVar[str] = "ping"


# --- sunucu → istemci ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Welcome:
    TYPE: ClassVar[str] = "welcome"

    protocol_version: int


@dataclass(frozen=True, slots=True)
class Rejected:
    """El sıkışma reddi. Sebep açıkça yazılır; bağlantı sessizce kapanmaz (§13)."""

    TYPE: ClassVar[str] = "rejected"

    reason: str
    server_version: int


@dataclass(frozen=True, slots=True)
class Transcript:
    """Çözümlenen metin. Segmenti ait olduğu tura bağlayan tek çerçeve."""

    TYPE: ClassVar[str] = "transcript"

    segment_id: str
    turn_id: str
    text: str


@dataclass(frozen=True, slots=True)
class StateChanged:
    """Durum değişikliği (§5).

    Durum sözlüğünün sahibi oturum aktörüdür; tip oradan geliyor. `transport → session`
    yönü §4'e uygun, tersi olamaz.
    """

    TYPE: ClassVar[str] = "state_changed"

    state: State
    turn_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolRunning:
    """Hangi tool'un çalıştığı (§6): tool sonucu dönene kadar ses üretilmiyor, kullanıcı
    sessizliğin sebebini görüyor."""

    TYPE: ClassVar[str] = "tool_running"

    turn_id: str
    tool_name: str


@dataclass(frozen=True, slots=True)
class Reply:
    """Seslendirilen cümlenin metni.

    Cümle başına bir çerçeve ve **kendi sesinden önce** gidiyor: TTS kuyruğunda paralellik
    yok (§6), yani sıra zaten cümlelerin sırası. Ayrı bir sayaç taşımıyor — `seq` sesin
    parçalarını sayıyor, bu ise cümleyi.
    """

    TYPE: ClassVar[str] = "reply"

    turn_id: str
    text: str


@dataclass(frozen=True, slots=True)
class AudioChunk:
    """Ses parçası. İkili çerçeve.

    `turn_id` tel formatının parçasıdır, sonradan eklenemez (§13): istemci kendi bildiği
    aktif turun dışındaki her parçayı sessizce atar, `seq` ile de sırayı doğrular.
    """

    TYPE: ClassVar[str] = "audio_chunk"

    turn_id: str
    seq: int
    format: AudioFormat
    data: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class AudioEnd:
    TYPE: ClassVar[str] = "audio_end"

    turn_id: str


@dataclass(frozen=True, slots=True)
class Cancelled:
    TYPE: ClassVar[str] = "cancelled"

    turn_id: str


@dataclass(frozen=True, slots=True)
class ErrorFrame:
    """Hata istemciye **ayrı ve bağımsız bir kanaldan** bildirilir (§14): TTS çöktüğünde
    sesli bildirim mümkün değildir."""

    TYPE: ClassVar[str] = "error"

    code: str
    message: str
    turn_id: str | None = None


@dataclass(frozen=True, slots=True)
class Announcement:
    """Proaktif bildirimin turunu açan çerçeve (§12).

    Zamanlanmış bir görev kullanıcı bir şey sormadan ses üretebilir ve o ses **kendi
    `turn_id`'sini** taşır. Ama §13'ün filtresi gereği istemci bilmediği turun parçasını
    atar; kullanıcının açmadığı bir turu ona duyuran tek çerçeve budur. `Transcript`'in
    yerini tutmuyor: transkript kullanıcının konuşmasını tura bağlar, burada konuşan
    kullanıcı değil.

    Durum değişikliği ile duyurulamazdı: proaktif ses bir tur değil ve §5'in tablosunda
    karşılığı yok — oraya bir geçiş uydurmak açık bir kararı kapatmak olurdu.
    """

    TYPE: ClassVar[str] = "announcement"

    turn_id: str
    text: str


@dataclass(frozen=True, slots=True)
class Pong:
    TYPE: ClassVar[str] = "pong"


type ClientFrame = Hello | SpeechSegment | TextSegment | Interrupt | Ping
type ServerFrame = (
    Welcome
    | Rejected
    | Transcript
    | StateChanged
    | ToolRunning
    | Reply
    | AudioChunk
    | AudioEnd
    | Cancelled
    | ErrorFrame
    | Announcement
    | Pong
)
type Frame = ClientFrame | ServerFrame

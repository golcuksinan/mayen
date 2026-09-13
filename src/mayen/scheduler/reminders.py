"""`reminder` türündeki görevin işleyicisi: yükteki metni proaktif kanaldan seslendirir.

Ayrı dosya, çünkü `loop.py` hangi türlerin olduğunu bilmiyor ve bilmemeli: tür → işleyici
eşlemesi montajda kuruluyor, yeni bir tür eklemek zamanlayıcıya dokunmuyor.
"""

from collections.abc import Awaitable, Callable

from mayen.data.repositories.tasks import ScheduledTask
from mayen.scheduler.announce import Announcer
from mayen.scheduler.loop import Handler

type Phrase = Callable[[str], Awaitable[str]]
"""Not → söylenecek cümle (`phrasing.ReminderVoice`).

Geri çağrım, çünkü bu dosyanın işi görevi açmak; cümlenin nasıl kurulduğu — model mi,
şablon mu, hiç mi — montajın kararı. Verilmezse not olduğu gibi okunur ve o hâl hâlâ
çalışan bir sistem: `main` bu ikisi arasında seçim yapıyor."""


def reminder_handler(announcer: Announcer, phrase: Phrase | None = None) -> Handler:
    async def run(task: ScheduledTask) -> str:
        message = task.payload.get("message")
        if not isinstance(message, str) or not message.strip():
            # Yük bozuk: görev kapanır ve sebebi satıra yazılır. Boş bir hatırlatıcıyı
            # seslendirmek, kullanıcıya sebepsiz bir ses çıkarmak olurdu.
            raise ValueError("hatırlatıcının metni yok")
        spoken = message if phrase is None else await phrase(message)
        turn_id = await announcer.announce(spoken)
        if turn_id is None:
            # Kuyruğa alındı (§12: ilk bağlanan cihaza verilir). Görev yine de kapanıyor:
            # `BEKLIYOR` bırakmak, her tik'te aynı metni kuyruğa bir kez daha eklerdi.
            return "kuyruklandı: bağlı cihaz yok"
        return f"seslendirildi: {turn_id}"

    return run

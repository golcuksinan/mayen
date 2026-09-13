"""Zamanlanmış görev — oluştur (§9.2, YAZMA).

Zaman damgası biçimi `data.clock`'unkiyle aynı olmak zorunda: iki biçim yazan iki yer,
kimsenin fark etmediği bozuk bir sıralama demektir. Bu yüzden burada doğrulanıyor —
geçersiz zaman modele geri beslenir, veritabanına yazılmaz.
"""

import re
from collections.abc import Mapping
from datetime import timedelta

from mayen.data import clock
from mayen.data.repositories.tasks import TaskKind
from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, text

#: Göreli biçim: `+8s`, `+5m`, `+2h`, `+3d`. Büyük harf de kabul — `+5M` reddetmek,
#: modelin yazım tercihini hata sayıp turu bir düzeltme turuna çevirmek olurdu.
_RELATIVE = re.compile(r"\+(\d+)([smhd])", re.IGNORECASE)
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _resolve(due: str) -> str:
    """`due`'yu saklanacak damgaya çevirir. Göreli biçimin dayanağı **şu an**.

    Göreli biçimin varlık sebebi ölçülmüş bir hata (2026-08-16, dolu geçmiş, 4 ifade × 6
    koşu): mutlak damga tek biçimken model aritmetiği kendi yapıyor ve altıda birinde
    dakika hanesini taşıyamıyordu — istenen 8 saniye, kurulan +65 saniye; sapmalar +12,
    +40, +52. Sahibin duyduğu buydu. Katalog metnine "dikkatli topla" yazmak bu sınıfa
    çare değil (P25'in ve rol metni turlarının ortak dersi); toplamayı **modelden almak**
    çare. Mutlak biçim duruyor, çünkü "yarın dokuzda" göreli olarak ifade edilemez.
    """
    due = due.strip()
    match = _RELATIVE.fullmatch(due)
    if match is None:
        # **UTC damgası artık reddediliyor, ve bu ölçülmüş bir karar (2026-08-17).** İlk
        # düzeltmede uyumluluk için kabul ediliyordu: "model doğru çevirmişse damga
        # doğrudur, reddetmek doğru bir zamanı hata saymak olur". Gerçek turda model
        # damga yazmaya devam etti (`2026-08-18T09:00:00Z` = yerel 12:00) ve o kabul
        # yolu hatayı **ayakta tuttu**.
        #
        # Ayrımın imkânsız olduğu yer burası: çevrilmiş bir damga ile çevrilmemiş bir
        # yerel saat aynı görünüyor. İki okuma arasında sessizce birini seçmek, üç saat
        # sapmayı sessizce seçmek. Reddetmek ise §8.3'ün geri beslemesine düşüyor —
        # model düzeltme turunda doğrusunu yazar ve düzeltme adım harcamaz.
        return clock.from_local(due)  # ValueError yükseltir; çağıran onu sonuca çeviriyor
    seconds = int(match.group(1)) * _UNITS[match.group(2).lower()]
    return clock.stamp(clock.parse(clock.now()) + timedelta(seconds=seconds))


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    try:
        due_at = _resolve(text(arguments, "due"))
    except ValueError:
        due = text(arguments, "due")
        return ToolResult(
            ok=False,
            error=f"{due!r}: zaman ya '2026-08-09 14:03' biçiminde yerel saat ya da"
            " +8s/+5m/+2h gibi göreli olmalı",
        )
    message = text(arguments, "message")
    task = context.tasks.create(TaskKind.REMINDER.value, {"message": message}, due_at)
    # **Yerel saat `data`'ya yazılıyor, `speech`'e değil** ve bunun sebebi ölçülmüş bir
    # yanılgı: `speech` üretimde **hiçbir yerden okunmuyor** (bkz. `spec.ToolResult`).
    # Cümleyi model yazıyor ve elindeki tek şey `_feedback()`'in verdiği `data`. Yalnızca
    # `due_at` konsaydı — ki 2026-08-16'ya kadar öyleydi — model saati UTC olarak okur ve
    # "Reminder set for 15:58:22 UTC" der; sahibin duyduğu buydu.
    local = clock.parse(task.due_at).astimezone().strftime(clock.LOCAL_FORMAT)
    return ToolResult(
        ok=True,
        data={"id": task.id, "due_local": local, "due_at": task.due_at, "message": message},
        speech=f"Reminder set for {local}.",
    )


TOOL = Tool(
    name="task_create",
    description="Belirtilen zamanda hatırlatılacak bir görev oluşturur.",
    effect=Effect.YAZMA,
    timeout_seconds=2.0,
    handler=_run,
    args=(
        Arg(
            "due",
            ArgType.STRING,
            # İki şey yazılı ve ikisi de ölçülmüş bir hatanın karşılığı (2026-08-16):
            # **alt sınırın yokluğu**, çünkü katalogda yazmayanı model yokluk sanıp
            # "birkaç dakikadan yakınına kuramam" diye reddediyordu (12 örnekte 2);
            # ve **göreli biçim önce**, çünkü mutlak damga tek seçenekken toplamayı model
            # yapıyor ve altıda birinde kaçırıyordu (`_resolve`'un başlığında sayılar).
            # Sıra kasıtlı: örneklerin ilki modelin ilk uzanacağı biçim.
            # Mutlak biçim **yerel saat** ve bu 2026-08-17'de ölçülmüş bir hatanın
            # karşılığı: UTC damgası istendiğinde model yerel saati damga alanına yazdı
            # ve hatırlatıcı saat dilimi kadar kaydı (bkz. `clock.from_local`). Öneğin
            # `utc` alanını taşıması yetmedi — dönüşümü modelden almak yetti.
            "Zaman. Göreli olarak yazılabilir (+8s, +5m, +2h, +3d) ya da mutlak yerel saat"
            " olarak (2026-08-09 14:03). Göreli biçim tercih edilir. Saat dilimi çevrimi"
            " yapılmaz, kullanıcının söylediği saat yazılır. En yakın zaman için alt sınır"
            " yoktur; birkaç saniye sonrası da kurulabilir.",
        ),
        Arg(
            "message",
            ArgType.STRING,
            # Zamanın buraya sızması gerçek modelde görüldü (2026-08-16): "10 saniye
            # sonra bi işim var" denince başlık "10 saniye önce hatırlatılan iş" oldu —
            # zaman içeriğe karışmış, üstelik geçmiş kipinde. Zaman zaten `due`'da;
            # açıklama artık ikisinin ayrı olduğunu ve metnin **kullanıcının işi**
            # olduğunu söylüyor.
            "Kullanıcıya okunacak hatırlatma metni: yapılacak işin kendisi."
            " Zaman bilgisi buraya yazılmaz, o `due` alanında.",
            trailing=True,
        ),
    ),
)

"""Bir veritabanı **kopyasını** geçmişteki bir tura geri sarar (Faz A/A1).

`issues.md` #7'nin teşhisi bir çıkarımdı: kayda bakıp "model cevabı zaten önünde gördüğü
için çağırmadı" denmişti. Onu ölçüme çeviren şey, o turda modele giden mesaj dizisini
**birebir** yeniden kurup tekrar göndermek. Ve o dizinin ne olduğunu bilen tek yer üretimin
kendisi: `memory.ContextWindow` + `memory.Recall` + `agent.prompt.build_messages`.

**Bu yüzden burada bir "geçmiş pencere kurucusu" yok, bir geri sarma var.** İkinci bir
pencere kurucusu yazmak P27'nin hatası olurdu — ölçüm, üretimin kurmadığı bir öneği ölçmeye
başlar ve bunu kimse fark etmez. Onun yerine kopyadaki gelecek siliniyor ve **üretimin
kendi kodu** çalıştırılıyor: o tarihte var olmayan hiçbir satır ortada kalmadığı için
`ContextWindow.build()` o turun penceresini kurar.

**Yalnızca bir kopya üzerinde.** Kural 1 dosyanın tek sahibi olduğunu söylüyor ve
`Database` bunu bir `flock` ile zorluyor; tekrar oynatma aracı önce sahipliği alıp
`backup_to()` ile kopyayı çıkarıyor, sonra kopyayı açıyor. Bu modülün sildikleri geri
alınamaz — üretim veritabanında çalıştırılması konuşmanın sonunu silmek olur.

**Sınır zaman değil, id + zaman.** Geçmiş `id` ile sıralanıyor (§11.1), yani mesajlarda
sınır `id`. Özet ve olgular ise turlar arasında, boşta üretiliyor: bir özet, kapsadığı
mesajlardan çok sonra yazılmış olabilir (`keep_recent` kadar geriden gelir). Bu yüzden
onların sınırı hedef mesajın `created_at`'i — `to_message < id` demek, o turda henüz
yazılmamış bir özeti varmış saymak olurdu.
"""

from dataclasses import dataclass

from mayen.data.db import Database, DatabaseError


@dataclass(frozen=True, slots=True)
class Rewound:
    """Neyin silindiği. Sayılar basılıyor: sessiz bir geri sarma, yanlış tura sarıldığını
    fark etmenin hiçbir yolunu bırakmazdı (Kural 13)."""

    message_id: int
    role: str
    content: str
    """Silinen hedef mesajın kendisi. Geri sarmadan **sonra** okunamaz, o yüzden burada:
    tekrar oynatma o cümleyi turun kullanıcı girdisi olarak yeniden veriyor."""
    person_id: int | None
    created_at: str
    messages: int
    summaries: int
    facts: int


def rewind(db: Database, message_id: int) -> Rewound:
    """Kopyayı `message_id` numaralı mesajın **yazılmasından hemen önceki** durumuna alır.

    Hedef mesajın kendisi de siliniyor: tur akışında kullanıcının cümlesi pencere
    kurulduktan **sonra** kaydediliyor (`turn/runner.py`), yani o tur kurulurken geçmişte
    yoktu. Silinmeseydi model kullanıcının sözünü iki kez görürdü — üretimde bir kez
    yapılmış ve düzeltilmiş hata.
    """
    with db.transaction() as conn:
        row = conn.execute(
            "SELECT role, person_id, content, created_at FROM messages WHERE id = ?",
            (message_id,),
        ).fetchone()
        if row is None:
            raise DatabaseError(f"Mesaj bulunamadı: {message_id}")
        created_at = str(row["created_at"])
        messages = conn.execute("DELETE FROM messages WHERE id >= ?", (message_id,)).rowcount
        summaries = conn.execute(
            "DELETE FROM summaries WHERE created_at > ?", (created_at,)
        ).rowcount
        facts = conn.execute("DELETE FROM facts WHERE created_at > ?", (created_at,)).rowcount
    return Rewound(
        message_id=message_id,
        role=str(row["role"]),
        content=str(row["content"]),
        person_id=row["person_id"],
        created_at=created_at,
        messages=messages,
        summaries=summaries,
        facts=facts,
    )

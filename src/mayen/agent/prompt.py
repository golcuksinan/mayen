"""Sabit önek düzeni (§8.1).

```
[sistem promptu (sabit)] [özet (varsa)] [konuşma geçmişi] [bağlam bloğu] [güncel tur]
```

**Bu dosyanın tek işi sırayı korumak.** Değişken içerik — tarih/saat, konuşmacı kimliği —
daima en sona, `bağlam bloğu`na yazılır; önekin bir baytı bile değişirse LLM sunucusunun KV
önbelleği düşer ve §8.1 bu kuralı pazarlığa kapalı ilan ediyor. Bu yüzden `build_messages`
mesaj dizisini elle sıralamıyor: sırayı bilen tek yer burası, çağıran parçaları verir.

**Sistem promptu bir kere kurulur, tur boyunca değişmez** (Kural 3). `system_prompt()`
defterden ve çağrı biçiminden üretiliyor; ikisi de süreç boyunca sabit olduğu için çıktı da
sabittir — katalog metni kayıt sırasında geziniyor (bkz. `tools/prompt.py`), yani aynı
defter aynı baytları veriyor.

**`system` rolü yalnızca ilk mesajda.** Özet, bağlam bloğu ve döngünün adım notu sıra
olarak yerlerinde duruyor ama rolleri `user`; içeriklerini `[özet]`, `[bağlam]`, `[not]`
etiketleri ayırıyor. Sebep ölçüldü: Qwen3.6'nın sohbet şablonu baştan sonra gelen bir
`system` mesajında `raise_exception('System message must be at the beginning…')` atıyor ve
llama-server 500 döndürüyor — tur, modelin ilk çağrısında ölüyordu. Ardışık iki `user`
mesajını aynı şablon sorunsuz kabul ediyor (denendi). Kural 3 bozulmuyor: tur boyunca
değişmeyen tek metin zaten ilk mesaj, ve değişken içerik yine sonda.

**Getirilen olgular (§11.3) bağlam bloğunun sonunda** ve metinlerini `memory` üretiyor.
Burada yalnızca bir alan var, biçim değil: kaynağı, tarihi ve "bayat olabilir" uyarısını
yazan taraf depoyu okuyan taraf (`memory/recall.py`), ve o metnin bloğun **sonunda**
durması §8.1'in sabit önek kuralının gereği — değişen içerik en sona.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from mayen.adapters.llm import PromptMessage
from mayen.agent.calls import CallFormat, instructions
from mayen.config import ConfigError
from mayen.tools.prompt import catalog_text
from mayen.tools.registry import Registry


@dataclass(frozen=True, slots=True)
class ContextBlock:
    """Turun değişken içeriği (§8.1). Öneğin **sonunda** durur, başında değil.

    `speaker` yalnızca bilgilendirmedir: yetkiyi `policy.authorize()` veriyor ve prompt bir
    güvenlik sınırı değil (Kural 4). Modelin bu satırı yok sayması bir güvenlik olayı değil.

    **Burada bir UTC damgası yok ve geri eklenmemeli (2026-08-17).** Vardı: "aynı an UTC
    (tool argümanları için)" satırı, `task_create`'in UTC isteyen `due` alanı içindi. İki
    alanı birlikte vermek dönüşümü güvenli kılmadı — model "yarın dokuzda" için
    `2026-08-18T09:00:00Z` yazdı, yani yerel saati damga alanına koydu ve hatırlatıcı
    dilim kadar (+03'te üç saat) kaydı. Tool artık yerel saat alıyor
    (`clock.from_local`); satır kaldıkça model **onu izliyor** ve aynı hatayı üretiyor.
    Ölçülmüş sıra bu: önce satır silindi, sonra hata bitti.
    """

    now: str
    """Yerel saat, insana okunacak biçimde (`clock.local()`). Model hem **konuşurken** hem
    `task_create`'in `due` alanını yazarken bunu kullanır — öneğin tek saat kaynağı."""
    speaker: str | None = None
    #: §11.3'ün getirilen olguları. Metni `memory` üretiyor — kaynağı, tarihi ve "bayat
    #: olabilir" uyarısı orada, çünkü biçimi bilen taraf depoyu okuyan taraf. Burada
    #: yalnızca **yeri** yazılı: bağlam bloğunun sonu, yani öneğin en sonu (§8.1).
    facts: str | None = None
    language_rule: str | None = None
    """§2'nin "çıkış İngilizce" kuralı — **yalnızca yerel çağrı biçiminde** burada.

    Faz 7 bu kuralın yerinin bir kaldıraç olduğunu ölçtü: rol metninin başında tutmuyor
    (18 cevapta ~2 İngilizce), sistem promptunun **sonuna**, katalogdan sonra konunca
    18/18 tutuyor. Yerel biçimde o yer artık ulaşılamıyor — katalogu sistem mesajına
    ekleyen taraf modelin sohbet şablonu ve `tools` bloğunu bizim metnimizin **arkasına**
    koyuyor. Sonuç elle koşuda görüldü: altı turun altısı Türkçe.

    Kalan en son nokta bağlam bloğunun sonu. Faz 7'nin "değişkenin arkasına koyma"
    yasağıyla çakışmıyor: bağlam bloğu **zaten** değişken ve zaten burada — kural onun
    kuyruğuna binerken sabit öneğin bir baytı bile değişmiyor. Yasaklanan şey öneğin
    sabit kuyruğundan **sonra yeni bir mesaj** açmaktı (ölçüldü: 22 → 1631 önek jetonu).

    Metin biçimlerinde `None`: orada kural sistem promptunun sonunda ve iki kopya, iki
    yerde bakımı yapılan bir metin olurdu."""

    def render(self) -> str:
        lines = ["[bağlam]", f"tarih/saat: {self.now}"]
        if self.speaker is not None:
            lines.append(f"konuşan: {self.speaker}")
        if self.facts is not None:
            lines.append(self.facts)
        if self.language_rule is not None:
            lines.append(self.language_rule)
        return "\n".join(lines)


def system_prompt(
    registry: Registry,
    call_format: CallFormat,
    *,
    role: str,
    language_rule: str | None = None,
) -> str:
    """Turlar boyunca değişmeyen önek başı (Kural 3).

    Üç parça: rol, çağrının nasıl yazılacağı (§8.3) ve katalog (§8.4). Sıra sabit; katalog
    en sonda, çünkü büyüyen tek parça o ve önündekilerin baytları sabit kalsın diye.

    **Rolün varsayılanı yok ve kodda bir kopyası da yok.** Metin yalnızca dosyada
    (`MAYEN_ROLE_PATH`); buraya bir yedek metin koymak, dosyayı düzenleyip hiçbir şeyin
    değişmediğini görmenin ya da iki metnin sessizce ayrışmasının yolu olurdu — `clock.py`
    ve `data/schedule.py`'nin dönem alanıyla aynı gerekçe.

    **Yalnızca `role` dışarıdan verilebiliyor.** Çağrı biçimi ve katalog defterden
    üretiliyor: onları elle yazılan bir dosyaya taşımak, tool eklendiğinde iki yerin
    güncellenmesini gerektirir ve biri unutulduğunda model var olmayan bir tool'u çağırır
    ya da var olanı hiç görmez — §9.1'in "ikinci, bağımsız metin" hatasının ta kendisi.
    """
    if call_format is CallFormat.YEREL:
        # Yerel biçimde **katalog ve çağrı sözdizimi buradan çıkıyor**: ikisini de modelin
        # kendi şablonu `tools` alanından yerleştiriyor. Bırakılsalardı model aynı defteri
        # iki kez, iki farklı sözdizimiyle görürdü — §9.1'in "ikinci, bağımsız metin"
        # hatası. Kalan: rol metni, ve arkasından dil kuralı (aşağıdaki gerekçe aynen).
        parts = [role]
    else:
        parts = [role, instructions(call_format), catalog_text(registry)]
    if language_rule is not None:
        # **Katalogdan sonra, yani sabit öneğin en sonunda.** §2'nin "çıkış İngilizce"
        # kararı rol metninin *başına* yazıldığında tutmuyor (üç ölçülü tur,
        # `docs/faz7-rol.md`): Türkçe girdi, geçmiş ve katalog tek bir yönergeden ağır
        # basıyor ve yalnızca en kısa selamlamalar İngilizce çıkıyor. Kaldıraç konum, ve
        # burası öneğin **değişken içeriğe değmeden** ulaşılabilen son noktası — bir
        # adım ötesi (kullanıcı mesajından sonrası) her turda tam prefill demek.
        parts.append(language_rule)
    return "\n\n".join(parts)


def load_role(path: Path) -> str:
    """Kişilik metnini dosyadan okur (düz metin, UTF-8).

    **Boş dosya hatadır**, boş rol değil — `data/schedule.py`'nin aynı gerekçesi: yolu
    yanlış yazılmış ya da kazara boşaltılmış bir dosyayı "rolü yok" diye okumak, asistanın
    kimliğini sessizce silmek olurdu. Okunamayan yol da `ConfigError`, sessiz varsayılan
    değil (Kural 13).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(f"Rol dosyası okunamadı: {path}") from error
    role = text.strip()
    if not role:
        raise ConfigError(f"Rol dosyası boş: {path}")
    return role


def build_messages(
    system: str,
    *,
    context: ContextBlock,
    user: str,
    summary: str | None = None,
    history: Sequence[PromptMessage] = (),
    turn: Sequence[PromptMessage] = (),
) -> tuple[PromptMessage, ...]:
    """§8.1'in mesaj dizisini kurar.

    `turn`, döngünün o tur içinde biriktirdikleri: modelin ürettiği çağrı ve geri beslenen
    tool sonucu (§8.2). Kullanıcının cümlesinden **sonra** gelirler; tool sonucu eklendikten
    sonraki çağrı ayrı bir istek değil, aynı öneğin devamıdır.

    **Değişken içerikten sonraya hiçbir şey eklenmiyor** ve bunun bedeli ölçüldü (Faz 7):
    dil kuralı kullanıcı mesajından *sonra* denendiğinde önbellek isabeti tamamen kayboldu —
    senaryo başına işlenen prompt jetonu 22'den 1631'e çıktı, yani her tur öneğin tamamını
    yeniden işledi ve TTFT 0.24'ten 1.04'e fırladı. Sabit bir metin olması yetmiyor;
    §8.1'in kuralı "değişken en sonda" ve değişkenin arkasına konan sabit de aynı bedeli
    ödetiyor. Kural `system_prompt()`'un sonuna gitti.
    """
    messages = [PromptMessage(role="system", content=system)]
    if summary is not None:
        messages.append(PromptMessage(role="user", content=f"[özet]\n{summary}"))
    messages.extend(history)
    messages.append(PromptMessage(role="user", content=context.render()))
    messages.append(PromptMessage(role="user", content=user))
    messages.extend(turn)
    return tuple(messages)

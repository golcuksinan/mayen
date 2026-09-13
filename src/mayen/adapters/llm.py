"""LLM servisi arayüzü (§3, §8).

Üç şey bilinçli olarak **burada değil**:

- **Tool çağrısının ayrıştırılması.** §8.3 çağrı biçimini ayrı bir adaptörün arkasına
  alıyor ve iki aday da aynı `ToolCall`'ı üretiyor. Buradan çıkan şey token akışı; onu
  `ToolCall`'a çeviren şey ajan katmanı (P6).
- **Token tahmini.** Kural 10: sayı sunucunun sayaç ucundan alınır. `count_tokens` bu
  yüzden arayüzün parçası — çağıran tarafın tahmin edebileceği bir yol bırakılmıyor.
- **Bağlam kurgusu.** Sabit önek düzeni (§8.1) ajanın işi; buraya hazır mesaj dizisi gelir.

**İptal (Kural 12):** `stream` bir async üreteç döndürür. Çağıran onu kapattığında —
`aclose()` ya da görevin iptali — üretim durur. Ayrı bir iptal jetonu yok; asyncio'nun
kendi mekanizması her aşamada zaten var olan iptal yolu, ikinci bir yol eklemek iki
yoldan birinin unutulması demek. Dönüş tipi bu yüzden `AsyncIterator` değil
`AsyncGenerator`: `aclose()` sözleşmenin parçası, uygulamanın rastlantısal bir ayrıntısı
değil — `AsyncIterator` söz verse de kapatmayı garanti etmezdi.
"""

from collections.abc import AsyncGenerator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from mayen.adapters.service import ModelService

type PromptRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class NativeCall:
    """Modelin **kendi** şablonunun taşıdığı tool çağrısı.

    `agent/calls.py:ToolCall` değil, bilerek: o tip §8.3'ün iki metin biçiminin ürünü ve
    defteri tanıyor. Bu, taşımanın seviyesindeki hâl — adı defterde var mı, argümanları
    geçerli mi, bunlara bakan taraf yukarıda (`Registry.get` + `Tool.validate`).

    Burada, `PromptMessage`'ın yanında duruyor çünkü çağrı iki yönde de geçiyor: modelden
    gelen yanıtta ve geçmişteki asistan mesajında. İkincisi olmadan model kendi geçmişinde
    hiç üretmediği bir biçim görür (`turn/runner.py`'nin aynı dersi).
    """

    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PromptMessage:
    """LLM'e giden tek mesaj.

    `data.conversation.Message` ile bilerek ayrı: o saklanan satır (id, `turn_id`, kişi,
    özet bağı), bu ise tele giden istek. Rol kümeleri de aynı değil — `system` saklanmaz,
    çünkü sistem promptu geçmişin parçası değil, önekin sabit başı (§8.1). Zaten §4 de
    bunu zorunlu kılıyor: `adapters`, `data`'nın altında ve onu import edemez.
    """

    role: PromptRole
    content: str
    tool_calls: tuple[NativeCall, ...] = ()
    """Asistan mesajının taşıdığı çağrılar — yalnızca yerel biçimde dolu.

    §8.3'ün iki metin biçiminde çağrı `content`'in **içinde** duruyor; orada bu alan boş
    kalır ve hiçbir şey değişmez. Ölçümde eklendi (2026-08-16, Faz B/2) ve eklenme sebebi
    bir ölçüm hatası: geçmişteki çağrı asistan **metni** olarak yazılınca model biçimi
    kopyaladı ve `{"name": "volume", …}` cümlesini sesli cevap olarak üretti. Model
    geçmişte kendi ürettiğini görmeli."""


class LLMClient(ModelService, Protocol):
    async def count_tokens(self, text: str) -> int:
        """Kural 10: tahmin yok. Bağlam bütçesi bu sayıya dayanır (§11.1)."""
        ...

    async def context_size(self) -> int:
        """Modelin gerçek bağlam boyutu, token cinsinden (§11.1).

        Sayaç gibi bu da **sorulur**, yapılandırmadan okunmaz: §11.1 bütçenin modelin
        gerçek boyutundan türetilmesini ve tek bir yerde tanımlanmasını istiyor. Ayrı bir
        ayar olsaydı, sunucu başka bir `-c` ile açıldığında iki bileşenin bağlam boyutu
        hakkında farklı fikri olurdu — §11.1'in adıyla yasakladığı şey tam olarak bu.
        """
        ...

    def stream(
        self,
        messages: Sequence[PromptMessage],
        *,
        grammar: str | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str]:
        """Yanıtı token token akıtır.

        `grammar`: GBNF. Verildiğinde model dilbilgisel olarak geçersiz çıktı üretemez
        (§8.3); tool çağrısı dalı sabit bir önekle başladığı için dallanma ilk token'da
        bellidir (§6). Gramer üretimi kayıt defterinin işi (P6), burası onu yalnızca
        taşır.
        """
        ...

    def stream_native(
        self,
        messages: Sequence[PromptMessage],
        *,
        tools: Sequence[dict[str, object]],
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str | NativeCall]:
        """Modelin **kendi** tool-calling şablonuyla akış (`CallFormat.YEREL`).

        `stream`'in kardeşi ve tek farkı çağrının nerede durduğu: katalog `tools` alanında
        şema olarak gidiyor (sistem promptunda metin olarak değil) ve çağrıyı sunucu
        ayrıştırıp `NativeCall` olarak veriyor. Gramer alınmıyor — şablonun kendi çağrı
        sözdizimini ikinci bir kısıtla ezmek onu bozardı.

        **Metin ile çağrı aynı akışta gelebilir** ve bu yöntemin var olma sebebi bu:
        `stream`'de dal ilk token'da seçiliyor (§6/C3), yani model bir üretimde ya
        konuşabiliyor ya çağırabiliyor. İkisini birden istediğinde çağrıyı düz metnin
        içinde taklit ediyor ve taklit sesli okunuyor (`docs/faz-b-yerel.md`).
        """
        ...

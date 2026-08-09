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

from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from mayen.adapters.service import ModelService

type PromptRole = Literal["system", "user", "assistant", "tool"]


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


class LLMClient(ModelService, Protocol):
    async def count_tokens(self, text: str) -> int:
        """Kural 10: tahmin yok. Bağlam bütçesi bu sayıya dayanır (§11.1)."""
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

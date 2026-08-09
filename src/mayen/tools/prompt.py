"""Katalog metninin sistem promptuna işlenmesi ve payının ölçülmesi (§8.4).

**Neden metin defterden üretiliyor:** §8.4 tüm tool'ların promptta bulunmasını istiyor,
model çalışma anında keşif yapmıyor. Elle yazılmış bir katalog metni, imzalarla arasındaki
farkı ancak model yanlış çağrı üretince belli eder — yani en pahalı yerde.

**Kural 10 — pay ölçülür, tahmin edilmez.** §8.4 bedelin ölçülmesini istiyor; ölçen sayı
LLM sunucusunun sayaç ucundan geliyor. `len(text) / 4` gibi bir tahmin, ölçüm diye
raporlanan bir uydurma olurdu.

Metin **sabit önekin** parçasıdır (§8.1): defter değişmedikçe baytı baytına aynı çıkar,
bu yüzden tool sıralaması kayıt sırasıdır ve hiçbir yerde sözlük gezinmesine bırakılmaz.
"""

from dataclasses import dataclass

from mayen.adapters.llm import LLMClient
from mayen.policy.effects import Effect
from mayen.tools.registry import Registry

_HEADER = (
    "Kullanabileceğin tool'lar aşağıda. Listede olmayan bir tool yoktur; "
    "bir tool'un burada yazılı olmayan argümanı da yoktur."
)

_APPROVAL_NOTE = "onay ister"


def catalog_text(registry: Registry) -> str:
    """§8.4'ün sistem promptuna giren katalog bloğu."""
    blocks = [_HEADER]
    for tool in registry:
        lines = [tool.usage(), f"  etki: {tool.effect.value}"]
        if tool.effect is Effect.GERI_ALINAMAZ:
            lines[-1] += f" ({_APPROVAL_NOTE})"
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


@dataclass(frozen=True, slots=True)
class CatalogSize:
    """Kataloğun bağlam bütçesindeki payı — §8.4'ün raporlamasını istediği sayı."""

    tokens: int
    budget: int

    @property
    def share(self) -> float:
        return self.tokens / self.budget


async def measure_catalog(registry: Registry, llm: LLMClient, budget: int) -> CatalogSize:
    """Katalog metninin kaç token tuttuğunu **sayaçtan** sorar (Kural 10).

    Pay bir eşikle karşılaştırılmıyor: §8.4 aşılınca keşif modelinin yeniden
    değerlendirilmesini söylüyor ama bir sayı vermiyor, o sayı da §19'da yok. Eşiği burada
    uydurmak, ölçümü kendi varsayımını doğrulayan bir teste çevirirdi.
    """
    if budget <= 0:
        raise ValueError("bağlam bütçesi pozitif olmalı")
    return CatalogSize(tokens=await llm.count_tokens(catalog_text(registry)), budget=budget)

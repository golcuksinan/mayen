"""Kalıcı olguların getirilmesi ve bağlam bloğuna yazılışı (§11.3).

§11.3 blokta üç şeyi şart koşuyor ve üçü de burada: olgunun **kaynağı**, **tarihi** ve
bunların **bayat olabileceği** — güncel veri gerekiyorsa tool çağrılmalı. Uyarı her seferde
yazılıyor: bir kez söylenip sonra düşen bir uyarı, olmayan uyarıdır.

**"İlgili olanlar" bugün yakınlık değil, tazelik + konuşan.** §11.3 ilgili olguların
getirilmesini istiyor ama ilgililiğin nasıl ölçüleceğini söylemiyor; anlamsal bir arama
gömü indeksi ister ve ne §19'da bir maddesi ne de ölçülmüş bir eşiği var. Uydurulmuş bir
benzerlik eşiği yerine iki sıralama kuralı yazıldı ve gerekçesi burada duruyor: **konuşanın
kendi olguları önce** (soruyu soran kişi hakkında bilinenler, başkası hakkında bilinenlerden
daha sık işe yarar), sonra **en yeniler**. Tavan `main.py`'de bir işletim değeri.

**Kişi adı olguya değil bloğa yazılıyor.** Depoda taşınan şey `person_id`; adı kayıt
anında metne gömmek, kişi yeniden adlandırıldığında sessizce yanlış bir kaynak göstermek
olurdu. Kural 7'nin tersi de burada geçerli: sistem verisi kullanıcının metin alanına
yazılmıyor, yalnızca okuma anında yan yana konuyor.
"""

from mayen.data.repositories.facts import Fact, FactRepository
from mayen.data.repositories.people import PeopleRepository

STALE_WARNING = (
    "Bu notlar geçmiş konuşmalardan kaldı ve bayat olabilir; güncel bilgi gerekiyorsa"
    " ilgili tool'u çağır."
)

"""§11.3'ün "bayat olabilir" uyarısı. **Açık ad, bilerek:** ölçüm de aynı metni kuruyor
(`evals/scenarios.py`) ve ikinci bir kopya yazılsaydı, uyarı değiştiğinde ölçüm eski metni
ölçmeye devam ederdi — `turn.runner.called_line`'ın ölçümde yeniden kullanılmasıyla aynı
gerekçe."""

_UNKNOWN = "tanınmayan biri"


class Recall:
    """Bağlam bloğuna giren olgu bölümünü üretir."""

    def __init__(
        self,
        facts: FactRepository,
        people: PeopleRepository,
        *,
        max_facts: int,
    ) -> None:
        if max_facts < 1:
            raise ValueError("max_facts en az 1 olmalı")
        self._facts = facts
        self._people = people
        self._max = max_facts

    def block(self, *, person_id: int | None = None) -> str | None:
        """Getirilen olgular, metin olarak. Hiç olgu yoksa `None` — boş bir başlık, modele
        "hatırladığım hiçbir şey yok" demenin gürültülü yolu olurdu."""
        selected = self._select(person_id)
        if not selected:
            return None
        lines = ["[hatırlananlar]"]
        lines.extend(
            f"- ({self._source(fact)}, {fact.created_at[:10]}) {fact.content}"
            for fact in selected
        )
        lines.append(STALE_WARNING)
        return "\n".join(lines)

    def _select(self, person_id: int | None) -> list[Fact]:
        facts = self._facts.list_all()
        facts.sort(key=lambda fact: (fact.person_id == person_id, fact.id), reverse=True)
        return facts[: self._max]

    def _source(self, fact: Fact) -> str:
        if fact.person_id is None:
            return _UNKNOWN
        person = self._people.get(fact.person_id)
        return person.name if person is not None else _UNKNOWN

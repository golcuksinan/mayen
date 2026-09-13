"""Bağlam bütçesi (§11.1). **Bağlam boyutunun tek yazıldığı yer burası.**

§11.1 iki şey söylüyor ve ikisi de bu dosyanın biçimini belirliyor:

- **Bütçe modelin gerçek bağlam boyutundan türetilir.** Sayı yapılandırmadan değil,
  servisin kendisinden geliyor (`LLMClient.context_size`). Ayrı bir ayar, sunucu başka bir
  `-c` ile açıldığında sessizce yanlış bir bütçe demekti.
- **Tek bir yerde tanımlanır.** Bu yüzden bölme burada yapılıyor: çağıran taraf yalnızca
  "sabit kısım şu kadar token" diyor ve geriye kalanı öğreniyor. Bölmeyi çağıranın
  yapması, ikinci bir bileşenin bağlam boyutu hakkında kendi fikrini edinmesi olurdu.

**Üretim payı ayrılıyor.** Bağlamın tamamını prompt'a vermek, modelin cevabını yazacak
yeri bırakmamak demek: sunucu ya cevabı ortasında keser ya da isteği reddeder. Payın
sayısı bir işletim değeri, ölçülmüş bir sabit değil — bu yüzden varsayılanı yok ve montaj
veriyor (`main.py`), tıpkı `max_steps` gibi.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Budget:
    """Bağlam boyutunun bölünmüş hâli."""

    context_size: int
    reserved_output: int

    def __post_init__(self) -> None:
        if self.context_size < 1:
            raise ValueError("context_size pozitif olmalı")
        if self.reserved_output < 1:
            raise ValueError("reserved_output pozitif olmalı")
        if self.reserved_output >= self.context_size:
            raise ValueError("üretim payı bağlamın tamamını yiyemez")

    def history_limit(self, fixed_tokens: int) -> int:
        """Sabit kısım (sistem promptu, özet, bağlam bloğu, kullanıcının cümlesi) çıktıktan
        sonra konuşma geçmişine kalan token sayısı.

        Negatife düşebilir ve **kırpılmıyor**: sabit kısım tek başına bağlamı aşıyorsa
        sorun geçmişin uzunluğu değil, bütçenin yanlış olması (§11.1) — sıfıra yuvarlamak
        o gerçeği çağırandan gizlerdi.
        """
        return self.context_size - self.reserved_output - fixed_tokens

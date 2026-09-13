"""Hatırlatıcının söylenen cümlesi. Kural 13'ün burada somut karşılığı: üretim düşerse
hatırlatıcı **susmuyor**, notun kendisi okunuyor."""

from mayen.adapters.fakes.llm import FakeLLM
from mayen.scheduler.phrasing import ReminderVoice

NOTE = "Su iç"


async def test_the_model_writes_the_spoken_sentence() -> None:
    """Duyulan şey notun kendisi değil: kullanıcının kendine yazdığı metin bir kayıt,
    asistanın söylediği bir cümle."""
    voice = ReminderVoice(FakeLLM(["I am reminding you to hydrate."]), "rol")
    assert await voice(NOTE) == "I am reminding you to hydrate."


async def test_the_note_travels_as_data_not_as_the_prompt() -> None:
    """Not modele **veri** olarak gidiyor; sistem promptu kişiliğin kendisi."""
    llm = FakeLLM(["Time to drink water."])
    await ReminderVoice(llm, "rol metni")(NOTE)
    system, user = llm.calls[0]
    assert system.content == "rol metni"
    assert NOTE in user.content


async def test_a_dead_service_reads_the_note_instead_of_going_silent() -> None:
    """Hatırlatıcının duyulmaması, kötü ifade edilmesinden pahalı (Kural 13)."""
    voice = ReminderVoice(FakeLLM(available=False), "rol")
    assert await voice(NOTE) == NOTE


async def test_an_empty_generation_reads_the_note() -> None:
    """Boş üretim gerçek modelde görülen bir şey; sessizlikle sonuçlanmamalı."""
    voice = ReminderVoice(FakeLLM(["   "]), "rol")
    assert await voice(NOTE) == NOTE


async def test_the_tool_branch_is_closed() -> None:
    """Bildirimde çağrılacak bir şey yok; açık bırakılan dal, cümle yerine çağrı
    üretilmesi demekti."""
    llm = FakeLLM(["Time to drink water."])
    await ReminderVoice(llm, "rol")(NOTE)
    assert llm.grammars[0] is not None

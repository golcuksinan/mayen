"""Onay sorusu yazıcısı ve cevap çözümleyicisi (§10.5), llama.cpp üzerinde.

Gramer llama.cpp'ye özgüdür: çözümleyici üç sözcükten başkasını üretemez, ayrıştırma aşaması
kalmaz. Modelin gördüğü her şey İngilizcedir (§8.6).
"""

import json
from collections.abc import Callable, Sequence

from openai import AsyncOpenAI

from mayen.ports.confirmation import PlannedCall, Resolution
from mayen.ports.models import NO_KEY, Endpoint

GRAMMAR = 'root ::= "CONFIRM" | "REJECT" | "UNCLEAR"'
WORDS = {
    "CONFIRM": Resolution.CONFIRM,
    "REJECT": Resolution.REJECT,
    "UNCLEAR": Resolution.UNCLEAR,
}

# v1'in promptu; daha sade, kavramla yazılmış bir sürümü ölçüldü ve dört modelde de daha
# kötü çıktı (örneksiz model Türkçe olumsuzluğu göremedi).
RESOLVER_SYSTEM = (
    "You are an intent classifier for user confirmation in an asymmetric voice assistant.\n"
    "The system asks confirmation in English, but the Administrator usually replies in "
    "Turkish (or English).\n\n"
    "Classify the user's response into exactly one token:\n"
    "- CONFIRM: The user agrees, approves, or repeats the action to be done.\n"
    "  Examples in Turkish: 'evet', 'sil', 'evet sil', 'tamam', 'onaylıyorum', 'yap', "
    "'olur', 'kapat'.\n"
    "  Examples in English: 'yes', 'confirm', 'confirmed', 'delete', 'please delete', "
    "'do it', 'sure'.\n"
    "- REJECT: The user explicitly refuses or cancels.\n"
    "  Examples in Turkish: 'hayır', 'iptal', 'vazgeç', 'silme', 'dur'.\n"
    "  Examples in English: 'no', 'cancel', 'don't', 'stop'.\n"
    "- UNCLEAR: The user asks an unrelated question or the intent is ambiguous."
)

WRITER_SYSTEM = (
    "You are a voice assistant about to perform actions that need the user's confirmation. "
    "Write exactly one short spoken question that states every action and asks whether to "
    "go ahead. Every argument value must appear in the sentence exactly as given. "
    "No markdown, no emoji. Language: {language}. Wrap anything not in that language — a "
    "name, a note body — in a tag with its two-letter language code, like "
    "<tr>süt alınacak</tr>."
)


class OutOfGrammarError(ValueError):
    """Çözümleyici üç sözcükten birini üretmedi; belirsiz sayılmaz (§10.5 adım 4)."""


def client(endpoint: Endpoint) -> AsyncOpenAI:
    key = endpoint.api_key.get_secret_value() if endpoint.api_key else NO_KEY
    return AsyncOpenAI(base_url=endpoint.base_url, api_key=key)


class LlamaCppQuestionWriter:
    def __init__(self, endpoint: Endpoint, language: Callable[[], str]) -> None:
        self._endpoint = endpoint
        self._client = client(endpoint)
        self._language = language  # sorunun yazıldığı an konuşanın dili

    async def write(self, calls: Sequence[PlannedCall]) -> str:
        plan = [
            {"tool": c.name, "description": c.description, "arguments": dict(c.arguments)}
            for c in calls
        ]
        response = await self._client.chat.completions.create(
            model=self._endpoint.model,
            messages=[
                {"role": "system", "content": WRITER_SYSTEM.format(language=self._language())},
                {"role": "user", "content": json.dumps(plan, ensure_ascii=False)},
            ],
            extra_body=dict(self._endpoint.body),
        )
        return (response.choices[0].message.content or "").strip()


class LlamaCppAnswerResolver:
    def __init__(self, endpoint: Endpoint) -> None:
        self._endpoint = endpoint
        self._client = client(endpoint)

    async def resolve(self, question: str, answer: str) -> Resolution:
        response = await self._client.chat.completions.create(
            model=self._endpoint.model,
            messages=[
                {"role": "system", "content": RESOLVER_SYSTEM},
                # Soru da verilir: v1'de soru verilmeyince "kapat" cevabı ret okunmuştu.
                {"role": "user", "content": f"Question: {question}\nAnswer: {answer}"},
            ],
            max_tokens=8,
            extra_body={**self._endpoint.body, "grammar": GRAMMAR},
        )
        word = (response.choices[0].message.content or "").strip()
        if word not in WORDS:
            raise OutOfGrammarError(word)
        return WORDS[word]

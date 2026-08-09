"""Kişiler — listele/getir (§9.2, OKUMA).

Ad verilmezse rehberin tamamı döner; verilirse ada göre süzülür. İki ayrı tool yapmak
kataloğu büyütür ve modele "listele mi getir mi" diye ikinci bir seçim ekler.
"""

from collections.abc import Mapping

from mayen.data.repositories.people import Person
from mayen.policy.effects import Effect
from mayen.tools.spec import Arg, ArgType, Tool, ToolContext, ToolResult, optional_text


def _fields(person: Person) -> dict[str, object]:
    return {"id": person.id, "name": person.name, "phone": person.phone}


async def _run(context: ToolContext, arguments: Mapping[str, object]) -> ToolResult:
    name = optional_text(arguments, "name")
    people = context.people.list_all()
    if name is not None:
        needle = name.casefold()
        people = [person for person in people if needle in person.name.casefold()]
    if not people:
        return ToolResult(ok=True, data={"contacts": []}, speech="No matching contact.")
    return ToolResult(
        ok=True,
        data={"contacts": [_fields(person) for person in people]},
        speech="; ".join(
            f"{person.name}{f' ({person.phone})' if person.phone else ''}" for person in people
        ),
    )


TOOL = Tool(
    name="contact_get",
    description="Rehberdeki kişileri listeler; ad verilirse ona göre süzer.",
    effect=Effect.OKUMA,
    timeout_seconds=2.0,
    handler=_run,
    args=(Arg("name", ArgType.STRING, "Aranacak kişi adı", required=False),),
)

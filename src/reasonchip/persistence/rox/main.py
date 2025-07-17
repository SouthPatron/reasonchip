#!/usr/bin/env python

import typing
import asyncio
import datetime

from reasonchip.persistence.rox.models import RoxModel, Field
from reasonchip.persistence.rox.rox import Rox, RoxConfiguration


class SammyModel(RoxModel):
    _schema: typing.ClassVar[str] = "sammy"


class PhoneNumber(SammyModel):
    location: typing.Literal["home", "work", "mobile"]
    country_code: str
    number: str


class Person(SammyModel):
    first_name: str
    first_name_two: "str"
    middle_name: typing.Optional[str] = None
    last_name: str
    age: int = Field(
        gt=0,
        le=120,
        description="Age in years",
    )
    phones: typing.List[PhoneNumber] = Field(default_factory=list)
    emergency_contact: typing.Optional[PhoneNumber] = None
    required_contact: PhoneNumber


async def main():
    config: RoxConfiguration = RoxConfiguration()

    Rox(config)

    person = Person(
        first_name="John",
        first_name_two="Doe",
        middle_name="Smith",
        last_name="Doe",
        age=30,
        phones=[
            PhoneNumber(
                location="home",
                country_code="+1",
                number="1234567890",
            ),
            PhoneNumber(
                location="work", country_code="+1", number="0987654321"
            ),
        ],
        required_contact=PhoneNumber(
            location="mobile", country_code="+1", number="5555555555"
        ),
        emergency_contact=PhoneNumber(
            location="home", country_code="+1", number="1112223333"
        ),
    )

    await person.save()

    assert person.id is not None

    person = await Person.load(person.id)
    assert person
    print(f"{person}")

    total_time = 0
    total_people = 1000

    for p in range(1, total_people):
        if p % 5 == 0:
            print(f"******************  {p}  *******************************")
            person.id = None
            if person.emergency_contact:
                person.emergency_contact.location = "home"
            person.last_name = "McCormick"
        elif p % 2 == 0:
            if person.emergency_contact:
                person.emergency_contact.location = "mobile"
            person.age = 35
            person.last_name = "Smith"
        else:
            if person.emergency_contact:
                person.emergency_contact.location = "work"
            person.age = 30
            person.last_name = "Doe"

        start_time = datetime.datetime.now()
        await person.save()
        end_time = datetime.datetime.now()

        diff_ms = (end_time - start_time).total_seconds() * 1000
        total_time += diff_ms

        print(f"REVISION: [{person.id}] {person._revision} [{diff_ms:.2f} ms]")

    average_time = total_time / total_people

    print(f"Average time to save: {average_time:.2f} ms")

    # new_id = await person.save()
    # print(f"New ID = [{new_id}]")
    # print(f"{person}")


if __name__ == "__main__":
    asyncio.run(main())

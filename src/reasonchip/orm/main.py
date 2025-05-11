#!/usr/bin/env python

import typing
import asyncio
import uuid

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_engine_from_config,
)

from reasonchip.orm.models import RoxModel, Field
from reasonchip.orm.rox import Rox


class PhoneNumber(RoxModel):
    location: typing.Literal["home", "work", "mobile"]
    country_code: str
    number: str


class Person(RoxModel):
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
    engine: AsyncEngine = async_engine_from_config(
        {
            "url": "postgresql+asyncpg://durand@/katana",
            "pool_size": 1,
            "max_overflow": 10,
            "pool_recycle": 300,
            "pool_timeout": 30,
        },
        prefix="",
    )

    Rox(engine=engine)

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
    )

    person = await Person.load(
        uuid.UUID("a95ceb26-e113-49a2-a602-bc73ff939243")
    )
    assert person
    print(f"{person}")

    for p in range(1, 10):
        print(f"REVISION: [{person.id}] {person._revision}")

        if p % 4 == 0:
            person.id = None

        await person.save()

    # new_id = await person.save()
    # print(f"New ID = [{new_id}]")
    # print(f"{person}")


if __name__ == "__main__":
    asyncio.run(main())

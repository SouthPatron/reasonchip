#!/usr/bin/env python

import typing
import asyncio
import uuid

from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_engine_from_config,
)

from reasonchip.orm.models import RoxModel
from reasonchip.orm.rox import Rox

# from reasonchip.orm.manager import RoxManager


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

    rox = Rox(engine=engine, schema="sammy")

    # man = RoxManager(rox=rox)
    # await man.initialize()

    person = Person(
        first_name="John",
        first_name_two="Doe",
        middle_name="Smith",
        last_name="Doe",
        age=30,
        phones=[
            PhoneNumber(
                location="home", country_code="+1", number="1234567890"
            ),
            PhoneNumber(
                location="work", country_code="+1", number="0987654321"
            ),
        ],
        required_contact=PhoneNumber(
            location="mobile", country_code="+1", number="5555555555"
        ),
    )

    print(f"{person}")

    new_id = await person.save()

    print(f"New ID = [{new_id}]")

    print(f"{person}")


if __name__ == "__main__":
    asyncio.run(main())

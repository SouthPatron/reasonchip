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
from reasonchip.orm.manager import RoxManager


class PhoneNumber(BaseModel):
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

    class Meta:
        class_uuid = "e30c0a66-6ee7-4854-9674-47c66236fb49"


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

    man = RoxManager(rox=rox)
    await man.initialize()

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
    )

    # print(f"{person}")
    # await man.save(person)

    obj = await man.load(
        Person,
        uuid.UUID("e7e5c864-9b2e-4d4e-99e1-c8344b8f0200"),
    )

    print(f"{obj}")


if __name__ == "__main__":
    asyncio.run(main())

import typing
import asyncio

import sqlalchemy as sa

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_engine_from_config,
)

from pydantic import BaseModel, Field

from models import RoxModel
from rox import Rox


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
    await rox.initialize()


if __name__ == "__main__":
    asyncio.run(main())

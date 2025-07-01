#!/usr/bin/env python

import typing
import asyncio
import uuid

from reasonchip.persistence.restful.restful import Restful
from reasonchip.persistence.restful.models import (
    RestfulModel,
    DefinedModel,
    DynamicModel,
    Relationship,
    relationship,
)

from auth.django_restful_token import DjangoRestfulTokenAuth


# Models


class CountryModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "country"

    id: typing.Optional[uuid.UUID] = None


class CountryShapeModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "country_shape"

    id: typing.Optional[uuid.UUID] = None


class CountryRelationshipModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "country_relationship"

    id: typing.Optional[uuid.UUID] = None


# *************************** MAIN *******************************************


async def main():
    url = "http://127.0.0.1:8000/api/restful/"
    url = url.rstrip("/")

    headers = {
        "Accept": "application/json",
    }

    auth = DjangoRestfulTokenAuth(
        login_url="/auth/token",
        username="reasonchip",
        password="stupid password",
    )

    restful = Restful(
        params={
            "base_url": url,
            "headers": headers,
        },
        auth=auth,
    )

    models = [
        CountryModel,
        CountryShapeModel,
        CountryRelationshipModel,
    ]

    async with restful as rf:

        for m in models:

            print(f"=========================== {m} =========================")

            rs = rf(m)
            page = await rs.filter()

            print("====== PAGE =============")
            print(page)
            print("====== END OF PAGE ======")

            if page:
                for item in page.results:
                    print("ITEM:")
                    print(item)
                    obj = await rs.load(item.id)

                    if obj:
                        print("OBJECT")
                        print(obj)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python

import typing
import asyncio
import uuid

from reasonchip.persistence.restful.restful import Restful
from reasonchip.persistence.restful.models import (
    DynamicModel,
    Relationship,
    relationship,
)

from auth.django_restful_token import DjangoRestfulTokenAuth


# *************************** MODELS *****************************************


class CountryModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "m/country"
    _field_name: typing.ClassVar[typing.Optional[str]] = "country"

    id: typing.Optional[uuid.UUID] = None


class CountryShapeModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "m/country_shape"
    _field_name: typing.ClassVar[typing.Optional[str]] = "country_shape"

    id: typing.Optional[uuid.UUID] = None
    country: typing.Optional[uuid.UUID] = None


class CountryRelationshipModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "m/country_relationship"
    _field_name: typing.ClassVar[typing.Optional[str]] = "country_relationship"

    id: typing.Optional[uuid.UUID] = None
    country: typing.Optional[uuid.UUID] = None
    foreign_country: typing.Optional[CountryModel] = relationship()


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

    models = [
        CountryModel,
        CountryShapeModel,
        CountryRelationshipModel,
    ]

    restful = Restful(
        params={
            "base_url": url,
            "headers": headers,
        },
        auth=auth,
        models=models,
    )

    await restful.init()

    # -----------------------------------------------------------------------

    async with restful as rf:

        # Countries
        countries = rf.objects.country
        rc = await countries.filter()
        if not rc:
            print("No countries found...")
        else:
            for c in rc:
                print(c)

        # Country Shapes
        shapes = rf.objects.country_shape
        rc = await shapes.filter()
        if not rc:
            print("No country shapes found...")
        else:
            for c in rc:
                print(c)

        # Country Relationship
        relationships = rf.objects.country_relationship
        rc = await relationships.filter()
        if not rc:
            print("No country relationships found...")
        else:
            for c in rc:
                print(c)


if __name__ == "__main__":
    asyncio.run(main())

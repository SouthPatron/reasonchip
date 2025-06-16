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


class PlayerModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "player"

    id: typing.Optional[uuid.UUID] = None


class MessageModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "message"

    id: typing.Optional[uuid.UUID] = None

    player: Relationship[PlayerModel] = relationship(PlayerModel)


class GameModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "game"

    id: typing.Optional[uuid.UUID] = None


class GameThreadModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "game_thread"

    id: typing.Optional[uuid.UUID] = None


class LocationModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "location"

    id: typing.Optional[uuid.UUID] = None


class LocationThreadModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "location_thread"

    id: typing.Optional[uuid.UUID] = None


class LocationSnapshotModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "location_snapshot"

    id: typing.Optional[uuid.UUID] = None


class CharacterModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "character"

    id: typing.Optional[uuid.UUID] = None


class CharacterProfileModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "character_profile"

    id: typing.Optional[uuid.UUID] = None


class CharacterThreadModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "character_thread"

    id: typing.Optional[uuid.UUID] = None


class PlayerAssociationModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "player_association"

    id: typing.Optional[uuid.UUID] = None


class GameConditionModel(DynamicModel):
    _endpoint: typing.ClassVar[str] = "game_condition"

    id: typing.Optional[uuid.UUID] = None


async def main():
    url = "http://127.0.0.1:8000/restful/"
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
        PlayerModel,
        MessageModel,
        GameModel,
        GameThreadModel,
        LocationModel,
        LocationThreadModel,
        LocationSnapshotModel,
        CharacterModel,
        CharacterProfileModel,
        CharacterThreadModel,
        PlayerAssociationModel,
        GameConditionModel,
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

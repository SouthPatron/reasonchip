#!/usr/bin/env python

import typing
import asyncio

from reasonchip.persistence.restful.restful import Restful
from reasonchip.persistence.restful.models import RestfulModel

from auth.django_restful_token import DjangoRestfulTokenAuth


class PlayerModel(RestfulModel):
    _endpoint: typing.ClassVar[str] = "player"


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

    async with restful as rf:
        rs = rf(PlayerModel)
        model = await rs.inspect()

        print(f"Model = {model}")


if __name__ == "__main__":
    asyncio.run(main())

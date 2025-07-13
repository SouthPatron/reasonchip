import typing
import httpx

from .models import RestfulModel
from .auth.auth_handler import AuthHandler
from .resolver import Resolver

from .restful_session import RestfulSession


class Restful:

    def __init__(
        self,
        models: typing.List[typing.Type[RestfulModel]],
        params: typing.Optional[typing.Dict[str, typing.Any]] = None,
        auth: typing.Optional[AuthHandler] = None,
    ):
        self._auth: typing.Optional[AuthHandler] = auth
        self._resolver: Resolver = Resolver(models)

        p = params or {}

        if "follow_redirects" not in p:
            p["follow_redirects"] = True

        self._session = httpx.AsyncClient(**p)

    async def __aenter__(self):
        return RestfulSession(
            session=self._session,
            resolver=self._resolver,
            auth=self._auth,
        )

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._session.aclose()

    # ---------------------- METHODS -----------------------------------------

    async def init(self) -> None:
        # Initialize all the models by the resolver
        await self._resolver.init(
            session=self._session,
            auth=self._auth,
        )

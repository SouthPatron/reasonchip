import typing
import httpx

from .auth.auth_handler import AuthHandler
from .resolver import Resolver


class ObjectProxy:

    def __init__(self, resolver: "Resolver"):
        self._resolver: "Resolver" = resolver

    def __getattr__(self, name: str) -> typing.Any:
        if name.startswith("_"):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )
        return self._resolver.resolve(name)


class RestfulSession:

    def __init__(
        self,
        session: httpx.AsyncClient,
        resolver: Resolver,
        auth: typing.Optional[AuthHandler] = None,
    ):
        self._session: httpx.AsyncClient = session
        self._resolver: Resolver = resolver
        self._auth: typing.Optional[AuthHandler] = auth

    @property
    def http_session(self) -> httpx.AsyncClient:
        return self._session

    @property
    def resolver(self) -> Resolver:
        return self._resolver

    @property
    def auth(self) -> typing.Optional[AuthHandler]:
        return self._auth

import typing
import httpx

from .auth.auth_handler import AuthHandler
from .resolver import Resolver
from .object_manager import ObjectManager


# -------------------- OBJECT PROXY ------------------------------------------


class ObjectProxy:

    def __init__(
        self,
        session: httpx.AsyncClient,
        resolver: Resolver,
        auth: typing.Optional[AuthHandler] = None,
    ):
        self._session: httpx.AsyncClient = session
        self._resolver: Resolver = resolver
        self._auth: typing.Optional[AuthHandler] = auth

    def __getattr__(self, name: str) -> ObjectManager:
        if name.startswith("_"):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

        model = self._resolver.get_model(name)
        objman = ObjectManager(
            session=self._session,
            model=model,
            auth=self._auth,
        )
        return objman


# -------------------- RESTFUL SESSION ---------------------------------------


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
        self._objects: ObjectProxy = ObjectProxy(
            session=session,
            resolver=resolver,
            auth=auth,
        )

    # ---------------- PROPERTIES --------------------------------------------

    @property
    def http_session(self) -> httpx.AsyncClient:
        return self._session

    @property
    def resolver(self) -> Resolver:
        return self._resolver

    @property
    def auth(self) -> typing.Optional[AuthHandler]:
        return self._auth

    @property
    def objects(self) -> ObjectProxy:
        return self._objects

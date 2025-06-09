import uuid
import typing
import httpx

from pydantic import (
    BaseModel,
    Field,
)
from auth.auth_handler import AuthHandler
from .models import (
    RestfulModel,
    DefinedModel,
    DynamicModel,
)

from .inspector import Inspector


RRT = typing.TypeVar("RRT", bound=BaseModel)


class RestfulResult(BaseModel, typing.Generic[RRT]):
    count: int
    next: typing.Optional[str] = None
    previous: typing.Optional[str] = None
    results: typing.List[RRT] = Field(default_factory=list)


class RestfulSession:

    def __init__(
        self,
        session: httpx.AsyncClient,
        model: typing.Type[RestfulModel],
        auth: typing.Optional[AuthHandler] = None,
    ):
        self._session: httpx.AsyncClient = session
        self._model: typing.Type[RestfulModel] = model
        self._auth: typing.Optional[AuthHandler] = auth

    async def _get_model(self) -> typing.Optional[typing.Type[RestfulModel]]:

        # If it's a defined model, we don't need to inspect
        if issubclass(self._model, DefinedModel):
            return self._model

        # Else it's a dynamic model and needs to be interpolated
        mod = await Inspector.inspect(
            session=self._session,
            model=self._model,
            auth=self._auth,
        )

        # Absorb fields into a new subclass of DynamicModel
        AbsorbedModel = type(
            f"Absorbed{self._model.__name__}", (DynamicModel, mod), {}
        )
        return AbsorbedModel

    async def get_page(
        self,
        page_no: int = 1,
        page_size: int = 20,
    ) -> typing.Optional[RestfulResult]:

        mod = self._model
        endpoint = "/m/" + mod._endpoint.rstrip("/") + "/"

        bm = await self._get_model()
        if not bm:
            raise RuntimeError(f"Unable to get model information: {mod}")

        # Authentication
        if self._auth:
            await self._auth.on_request(self._session)

        # Handle parameters
        params = {"page": page_no, "page_size": page_size}

        # Perform request
        resp = await self._session.get(endpoint, params=params)
        if resp.status_code != 200:

            # Handle authentication errors
            if resp.status_code == 401 and self._auth:
                await self._auth.on_forbidden(self._session)
                return await self.get_page(
                    page_no,
                    page_size,
                )

            # Probably page not found
            if resp.status_code == 404:
                return None

            raise RuntimeError(
                f"Unable to get page: {mod}: {resp.status_code} - {resp.text}"
            )

        rc = resp.json()

        RestfulPageModel = RestfulResult[bm]
        return RestfulPageModel.model_validate(rc)

    async def load(
        self,
        oid: uuid.UUID,
    ) -> typing.Optional[RestfulModel]:

        mod = self._model
        endpoint = "/m/" + mod._endpoint + f"/{oid}/"

        bm = await self._get_model()
        if not bm:
            raise RuntimeError(f"Unable to get model information: {mod}")

        # Get the
        resp = await self._session.get(endpoint)
        if resp.status_code == 200:
            rc = bm.model_validate(resp.content)
            return rc

        # Handle authentication errors
        if resp.status_code == 401 and self._auth:
            await self._auth.on_forbidden(self._session)
            return await self.load(oid=oid)

        # Probably page not found
        if resp.status_code == 404:
            return None

        raise RuntimeError(
            f"Unable to get object: {mod}: {oid} {resp.status_code} - {resp.text}"
        )


class Restful:

    def __init__(
        self,
        params: typing.Optional[typing.Dict[str, typing.Any]] = None,
        auth: typing.Optional[AuthHandler] = None,
    ):
        self._auth: typing.Optional[AuthHandler] = auth

        p = params or {}

        if "follow_redirects" not in p:
            p["follow_redirects"] = True

        self._session = httpx.AsyncClient(**p)

    async def __aenter__(self):
        def create_rs(rm: typing.Type[RestfulModel]) -> RestfulSession:
            return RestfulSession(
                session=self._session,
                model=rm,
                auth=self._auth,
            )

        return create_rs

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._session.aclose()

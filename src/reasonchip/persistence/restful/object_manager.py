import uuid
import typing
import httpx

from pydantic import BaseModel, Field

from .models import RestfulModel
from .auth.auth_handler import AuthHandler
from .query import Query


RRT = typing.TypeVar("RRT", bound=BaseModel)


class RestfulResult(BaseModel, typing.Generic[RRT]):
    count: int
    next: typing.Optional[str] = None
    previous: typing.Optional[str] = None
    results: typing.List[RRT] = Field(default_factory=list)


class ObjectManager:

    def __init__(
        self,
        session: httpx.AsyncClient,
        model: typing.Type[RestfulModel],
        auth: typing.Optional[AuthHandler] = None,
    ):
        self._session: httpx.AsyncClient = session
        self._model: typing.Type[RestfulModel] = model
        self._auth: typing.Optional[AuthHandler] = auth

    # ---------------------------- LISTING -----------------------------------

    async def filter(
        self,
        query: typing.Optional[Query] = None,
    ) -> typing.Optional[RestfulResult]:

        mod = self._model
        endpoint = mod._endpoint.strip("/") + "/"

        if self._auth:
            await self._auth.on_request(self._session)

        params = query.to_params() if query else {}

        resp = await self._session.get(endpoint, params=params)

        if resp.status_code == 200:
            rc = resp.json()
            from pprint import pprint

            pprint(rc)

            RestfulPageModel = RestfulResult[mod]
            return RestfulPageModel.model_validate(rc)

        if resp.status_code == 401 and self._auth:
            await self._auth.on_forbidden(self._session)
            return await self.filter(query=query)

        if resp.status_code == 404:
            return None

        raise RuntimeError(
            f"Unable to filter: {mod}: {resp.status_code} - {resp.text}"
        )

    # ---------------------------- CRUD --------------------------------------

    async def create(
        self,
        data: typing.Union[RestfulModel, dict],
    ) -> typing.Optional[RestfulModel]:

        mod = self._model
        endpoint = mod._endpoint.strip("/") + "/"

        # Authentication
        if self._auth:
            await self._auth.on_request(self._session)

        payload = data.model_dump() if isinstance(data, BaseModel) else data

        resp = await self._session.post(endpoint, json=payload)

        if resp.status_code == 201:
            return mod.model_validate(resp.json())

        if resp.status_code == 401 and self._auth:
            await self._auth.on_forbidden(self._session)
            return await self.create(data=data)

        raise RuntimeError(
            f"Unable to create object: {mod}: {resp.status_code} - {resp.text}"
        )

    async def load(
        self,
        oid: uuid.UUID,
    ) -> typing.Optional[RestfulModel]:

        mod = self._model
        endpoint = mod._endpoint.strip("/") + f"/{oid}/"

        # Authentication
        if self._auth:
            await self._auth.on_request(self._session)

        # Get the object
        resp = await self._session.get(endpoint)

        # Successful retrieval
        if resp.status_code == 200:
            rc = mod.model_validate(resp.json())
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

    async def update(
        self,
        oid: uuid.UUID,
        data: typing.Union[RestfulModel, dict],
    ) -> typing.Optional[RestfulModel]:

        mod = self._model
        endpoint = mod._endpoint.strip("/") + f"/{oid}/"

        # Authentication
        if self._auth:
            await self._auth.on_request(self._session)

        payload = data.model_dump() if isinstance(data, BaseModel) else data

        resp = await self._session.put(endpoint, json=payload)

        if resp.status_code == 200:
            return mod.model_validate(resp.json())

        if resp.status_code == 401 and self._auth:
            await self._auth.on_forbidden(self._session)
            return await self.update(oid=oid, data=data)

        raise RuntimeError(
            f"Unable to update object: {mod}: {oid} {resp.status_code} - {resp.text}"
        )

    async def delete(
        self,
        oid: uuid.UUID,
    ) -> bool:

        mod = self._model
        endpoint = mod._endpoint.strip("/") + f"/{oid}/"

        # Authentication
        if self._auth:
            await self._auth.on_request(self._session)

        resp = await self._session.delete(endpoint)

        if resp.status_code == 204:
            return True

        if resp.status_code == 401 and self._auth:
            await self._auth.on_forbidden(self._session)
            return await self.delete(oid=oid)

        if resp.status_code == 404:
            return False

        raise RuntimeError(
            f"Unable to delete object: {mod}: {oid} {resp.status_code} - {resp.text}"
        )

import uuid
import typing
import httpx

from pydantic import (
    BaseModel,
    Field,
)

from .models import RestfulModel


class RestfulResult(BaseModel):
    count: int
    next: typing.Optional[str] = None
    previous: typing.Optional[str] = None
    results: typing.List[RestfulModel] = Field(default_factory=list)


class RestfulSession:

    def __init__(
        self,
        session: httpx.AsyncClient,
        model: typing.Type[RestfulModel],
    ):
        self._session: httpx.AsyncClient = session
        self._model: typing.Type[RestfulModel] = model

    async def load(
        self,
        oid: uuid.UUID,
    ) -> typing.Optional[RestfulModel]:

        mod = self._model
        endpoint = mod._endpoint + f"/{oid}/"

        async with self._session as client:
            resp = await client.get(endpoint)
            if resp.status_code == 200:
                rc = mod.model_validate(resp.content)
                return rc

            return None


class Restful:

    def __init__(
        self,
        params: typing.Optional[dict] = None,
    ):
        p = params or {}
        self._session = httpx.AsyncClient(**p)

    async def __aenter__(self):
        def create_rs(rm: typing.Type[RestfulModel]) -> RestfulSession:
            return RestfulSession(
                session=self._session,
                model=rm,
            )

        return create_rs

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

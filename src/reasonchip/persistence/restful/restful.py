import uuid
import typing
import httpx

from datetime import datetime

from pydantic import (
    BaseModel,
    Field,
    create_model,
)

from auth.auth_handler import AuthHandler
from .models import RestfulModel


class RestfulResult(BaseModel):
    count: int
    next: typing.Optional[str] = None
    previous: typing.Optional[str] = None
    results: typing.List[RestfulModel] = Field(default_factory=list)


def generate_model_from_post_schema(
    schema: typing.Dict[str, typing.Any],
    model_name: str,
) -> typing.Type[BaseModel]:

    fields = {}

    for field_name, meta in schema.items():

        field_type: typing.Any
        default: typing.Any = None

        field_type = meta["type"]

        if field_type == "string":
            field_type = str

        elif field_type == "datetime":
            field_type = datetime

        elif field_type == "choice":
            field_type = str

        else:
            print(
                f"Warning: Unsupported field type '{field_type}' for field '{field_name}' in model '{model_name}'"
            )
            assert (
                False
            ), f"Unsupported field type '{field_type}' for field '{field_name}' in model '{model_name}'"
            field_type = typing.Any

        # Optional if not required or read_only
        if not meta.get("required", False) or meta.get("read_only", False):
            field_type = typing.Optional[field_type]
            default = None

        # You could enhance this with constraints (max_length, choices, etc.)
        fields[field_name] = (
            field_type,
            Field(
                default=default,
                description=meta.get("label", ""),
            ),
        )

    model = create_model(model_name, **fields)
    return model


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

    async def inspect(self):
        mod = self._model
        endpoint = "/m/" + mod._endpoint.rstrip("/") + "/"

        async with self._session as client:

            # Authentication
            if self._auth:
                await self._auth.on_request(client)

            # Perform request
            resp = await client.options(endpoint)
            if resp.status_code != 200:

                if resp.status_code == 401 and self._auth:
                    await self._auth.on_forbidden(client)
                    return await self.inspect()

                raise RuntimeError("Unable to fetch OPTIONS")

            rc = resp.json()

            print(f"RC = {rc}")

            post_schema = resp.json()["actions"]["POST"]
            model_name = mod.__name__

            new_model = generate_model_from_post_schema(
                schema=post_schema,
                model_name=model_name,
            )

            return new_model

    async def load(
        self,
        oid: uuid.UUID,
    ) -> typing.Optional[RestfulModel]:

        mod = self._model
        endpoint = "/m/" + mod._endpoint + f"/{oid}/"

        async with self._session as client:
            resp = await client.get(endpoint)
            if resp.status_code == 200:
                rc = mod.model_validate(resp.content)
                return rc

            return None


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
        pass

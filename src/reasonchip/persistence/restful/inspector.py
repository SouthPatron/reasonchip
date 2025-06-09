import typing
import httpx
import asyncio

from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    create_model,
)
from auth.auth_handler import AuthHandler
from .models import RestfulModel


class Inspector:

    _lock: asyncio.Lock = asyncio.Lock()
    _registry: typing.Dict[str, typing.Type[BaseModel]] = {}

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Inspector is singleton.")

    @classmethod
    async def inspect(
        cls,
        session: httpx.AsyncClient,
        model: typing.Type[RestfulModel],
        auth: typing.Optional[AuthHandler] = None,
    ):

        async with cls._lock:

            # Check for local cache
            key_name = model.__name__
            if key_name in cls._registry:
                return Inspector._registry[key_name]

            # The remote needs to be inspected and a model generated.
            endpoint = "/m/" + model._endpoint.rstrip("/") + "/"

            # Authentication
            if auth:
                await auth.on_request(session)

            # Perform request
            resp = await session.options(endpoint)
            if resp.status_code != 200:

                if resp.status_code == 401 and auth:
                    await auth.on_forbidden(session)
                    return await cls.inspect(session, model, auth)

                raise RuntimeError("Unable to fetch OPTIONS")

            rc = resp.json()

            post_schema = rc["actions"]["POST"]
            model_name = model.__name__

            new_model = cls._model_from_schema(
                schema=post_schema,
                model_name=model_name,
            )

            Inspector._registry[key_name] = new_model
            return new_model

    @classmethod
    def _model_from_schema(
        cls,
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
                # field_type = typing.Any

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

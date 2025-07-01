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

    def __init__(self):
        self._lock: asyncio.Lock = asyncio.Lock()
        self._registry: typing.Dict[str, typing.Type[BaseModel]] = {}

    async def inspect(
        self,
        session: httpx.AsyncClient,
        model: typing.Type[RestfulModel],
        auth: typing.Optional[AuthHandler] = None,
    ):

        async with self._lock:

            # Check for local cache
            key_name = model.__name__
            if key_name in self._registry:
                return self._registry[key_name]

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
                    return await self.inspect(session, model, auth)

                raise RuntimeError("Unable to fetch OPTIONS")

            rc = resp.json()

            post_schema = rc["actions"]["POST"]
            model_name = model.__name__

            new_model = self._model_from_schema(
                model=model,
                schema=post_schema,
                model_name=model_name,
            )

            self._registry[key_name] = new_model
            return new_model

    def _model_from_schema(
        self,
        model: typing.Type[RestfulModel],
        schema: typing.Dict[str, typing.Any],
        model_name: str,
    ) -> typing.Type[BaseModel]:

        # Original fields take precedence over # generated fields
        original_fields = model.model_fields

        # Now merge the original fields with the generated fields
        fields = {}
        for field_name, meta in schema.items():

            # Check to see if it exists already
            if field_name in original_fields:
                f = original_fields[field_name]

                fields[field_name] = (
                    f.annotation,
                    Field(
                        default=f.default,
                        description=meta.get("label", ""),
                    ),
                )
                continue

            # Create it
            field_type: typing.Any
            default: typing.Any = None

            field_type = meta["type"]

            if field_type == "string":
                field_type = str

            elif field_type == "boolean":
                field_type = bool

            elif field_type == "datetime":
                field_type = datetime

            elif field_type == "choice":
                field_type = str

            else:

                print(f"========= BEGIN: SCHEMA ============")
                print(schema)
                print(f"========= END: SCHEMA ==============")

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

        m = create_model(model_name, **fields)
        return m

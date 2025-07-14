import typing
import httpx
import asyncio

from dataclasses import dataclass

from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    create_model,
)
from auth.auth_handler import AuthHandler
from .models import (
    RestfulModel,
    DefinedModel,
    DynamicModel,
    Relationship,
)


@dataclass
class ModelInfo:
    model: typing.Type[RestfulModel]
    inspected_model: typing.Optional[typing.Type[BaseModel]] = None


class Resolver:

    def __init__(
        self,
        models: typing.List[typing.Type[RestfulModel]],
    ):
        self._lock: asyncio.Lock = asyncio.Lock()
        self._registry: typing.Dict[str, ModelInfo] = {}

        for x in models:
            field_name = x._field_name if x._field_name else x._endpoint
            assert (
                field_name not in self._registry
            ), f"Model '{field_name}' already exists in registry."
            self._registry[field_name] = ModelInfo(model=x)

    @property
    def models(self) -> typing.Dict[str, typing.Type[RestfulModel]]:
        rc = {}

        for k, v in self._registry.items():
            assert v.inspected_model, "Init was not called before use."
            rc[k] = v

        return rc

    # ----------------- INITIALIZATION --------------------------------------

    async def init(
        self,
        session: httpx.AsyncClient,
        auth: typing.Optional[AuthHandler] = None,
    ):
        for k, _ in self._registry.items():
            im: typing.Type[BaseModel] = await self._inspect(
                session,
                field_name=k,
                auth=auth,
            )

    def get_model(self, field_name: str):
        assert (
            field_name in self._registry
        ), f"Model '{field_name}' not found in registry."

        mi = self._registry[field_name]
        assert (
            mi.inspected_model
        ), f"Model '{field_name}' has not been inspected yet."
        return mi.inspected_model

    # ----------------- INSPECTION ------------------------------------------

    async def _inspect(
        self,
        session: httpx.AsyncClient,
        field_name: str,
        auth: typing.Optional[AuthHandler] = None,
    ) -> typing.Type[BaseModel]:

        async with self._lock:

            # Check for local cache
            if field_name not in self._registry:
                raise RuntimeError(
                    f"Model '{field_name}' not found in registry."
                )

            # Check if already inspected
            entry = self._registry[field_name]
            if entry.inspected_model:
                return entry.inspected_model

            # If it's a DefinedModel class, it is exactly what is says it is.
            if issubclass(entry.model, DefinedModel):
                entry.inspected_model = entry.model
                return entry.inspected_model

            # The remote needs to be inspected and a model generated.
            model = entry.model

            endpoint = model._endpoint.strip("/") + "/"

            # Authentication
            if auth:
                await auth.on_request(session)

            # Perform request
            resp = await session.options(endpoint)
            if resp.status_code != 200:

                if resp.status_code == 401 and auth:
                    await auth.on_forbidden(session)
                    return await self._inspect(session, field_name, auth)

                raise RuntimeError("Unable to fetch OPTIONS")

            rc = resp.json()

            post_schema = rc["actions"]["POST"]
            model_name = model.__name__

            new_model = self._model_from_schema(
                model=model,
                schema=post_schema,
                model_name=model_name,
            )

            # Copy accross the important model variables
            setattr(new_model, "_endpoint", model._endpoint)
            setattr(new_model, "_field_name", model._field_name)

            # Registry
            self._registry[field_name] = ModelInfo(
                model=model,
                inspected_model=new_model,
            )

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

                # This is not a relationship
                if not isinstance(f.default, Relationship):
                    fields[field_name] = (
                        f.annotation,
                        Field(
                            default=f.default,
                            description=meta.get("label", ""),
                        ),
                    )
                    continue

                # ------------------ Generate the field -----------------------
                rel: Relationship = f.default

                field_kwargs = {}

                # Defaults
                if rel.default_factory:
                    field_kwargs["default_factory"] = rel.default_factory
                else:
                    field_kwargs["default"] = rel.default

                # Simple field values
                field_kwargs["description"] = rel.description

                # Create the field now
                field = Field(**field_kwargs)

                # Deliver the field
                fields[field_name] = (f.annotation, field)
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

            elif field_type == "field":
                if field_name not in self._registry:
                    print(f"========= BEGIN: SCHEMA ============")
                    print(schema)
                    print(f"========= END: SCHEMA ==============")
                    assert (
                        False
                    ), f"Field type '{field_name}' not found in registry in model '{model_name}'"

                mi = self._registry[field_name]
                field_type = mi.model

            else:
                print(f"========= BEGIN: SCHEMA ============")
                print(schema)
                print(f"========= END: SCHEMA ==============")
                assert (
                    False
                ), f"Unsupported field type '{field_type}' for field '{field_name}' in model '{model_name}'"

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

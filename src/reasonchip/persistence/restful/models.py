from __future__ import annotations

import uuid
import typing

from pydantic import (
    BaseModel,
    Field,
    create_model,
)


class RestfulModel(BaseModel):
    _endpoint: typing.ClassVar[str]


def generate_model_from_post_schema(
    schema: typing.Dict[str, typing.Any],
    model_name: str,
) -> typing.Type[BaseModel]:

    fields = {}

    for field_name, meta in schema.items():
        field_type: typing.Any
        default: typing.Any = None

        if meta["type"] == "string":
            field_type = str

        elif meta["type"] == "datetime":
            from datetime import datetime

            field_type = datetime

        elif meta["type"] == "choice":
            field_type = str

        else:
            field_type = typing.Any

        # Optional if not required or read_only
        if not meta.get("required", False) or meta.get("read_only", False):
            field_type = typing.Optional[field_type]
            default = None

        # You could enhance this with constraints (max_length, choices, etc.)
        fields[field_name] = (
            field_type,
            Field(default=default, description=meta.get("label", "")),
        )

    model = create_model(model_name, **fields)
    return model

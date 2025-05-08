from __future__ import annotations

import uuid
import typing

from pydantic import BaseModel, Field

from .utils import pascal_to_snake


class RoxModelMeta:
    table_name: str
    class_uuid: uuid.UUID

    _required_meta_fields: typing.List[str] = [
        "class_uuid",
    ]


class RoxRegistry:
    _registry: typing.Dict[uuid.UUID, typing.Type[RoxModel]] = {}


class RoxModel(BaseModel):

    # Common field for all Rox models
    id: typing.Optional[uuid.UUID] = None
    version: int = Field(default=1, frozen=True)

    # Registry management for RoxModel
    def __init_subclass__(cls):
        super().__init_subclass__()

        classname = pascal_to_snake(cls.__name__)

        # Check the Meta class
        meta = getattr(cls, "Meta", None)
        if meta is None:
            raise TypeError(f"{cls.__name__}.Meta must be defined")

        for f in RoxModelMeta._required_meta_fields:
            if not hasattr(meta, f):
                raise TypeError(
                    f"{cls.__name__}.Meta must define {f} attribute"
                )

        if not hasattr(meta, "table_name"):
            meta.table_name = classname

        # Register into the factory
        class_uuid = meta.class_uuid
        if class_uuid in RoxRegistry._registry:
            raise TypeError(
                f"UUID {class_uuid} ({cls}) already registered for {RoxRegistry._registry[class_uuid]}"
            )

        RoxRegistry._registry[class_uuid] = cls

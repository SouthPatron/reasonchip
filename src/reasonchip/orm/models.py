import uuid
import typing
import re

from pydantic import BaseModel, Field


def pascal_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class RoxModelMeta:
    table_name: str
    class_uuid: uuid.UUID

    _required_meta_fields: typing.List[str] = [
        "class_uuid",
    ]


class RoxModel(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id")

    def __init_subclass__(cls):
        super().__init_subclass__()

        classname = pascal_to_snake(cls.__name__)

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

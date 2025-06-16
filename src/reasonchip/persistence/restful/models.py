from __future__ import annotations

import typing

from pydantic import BaseModel


class RestfulModel(BaseModel):
    _endpoint: typing.ClassVar[str]


class DefinedModel(RestfulModel):
    pass


class DynamicModel(RestfulModel):
    pass


T = typing.TypeVar("T", bound="RestfulModel")


class Relationship(typing.Generic[T]):
    def __init__(
        self,
        model: typing.Type[T],
    ):
        self.model = model


def relationship(
    model: typing.Type[T],
) -> Relationship[T]:
    return Relationship[T](
        model=model,
    )

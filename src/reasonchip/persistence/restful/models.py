from __future__ import annotations

import typing

from dataclasses import dataclass

from pydantic import BaseModel

# --------------------------- MODELS ----------------------------------------


class RestfulModel(BaseModel):
    _endpoint: typing.ClassVar[str]
    _field_name: typing.ClassVar[typing.Optional[str]] = None


class DefinedModel(RestfulModel):
    pass


class DynamicModel(RestfulModel):
    pass


# -------------------------- RELATIONSHIPS ----------------------------------


@dataclass
class Relationship:
    default: typing.Any = None
    default_factory: typing.Optional[typing.Callable] = None
    description: typing.Optional[str] = None


def relationship(
    default: typing.Any = None,
    default_factory: typing.Optional[typing.Callable] = None,
    description: typing.Optional[str] = None,
) -> typing.Any:

    if default and default_factory:
        raise ValueError("Cannot specify both default and default_factory")

    return Relationship(
        default=default,
        default_factory=default_factory,
        description=description,
    )

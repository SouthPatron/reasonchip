from __future__ import annotations

import typing

from pydantic import BaseModel


class RestfulModel(BaseModel):
    _endpoint: typing.ClassVar[str]


class DefinedModel(RestfulModel):
    pass


class DynamicModel(RestfulModel):
    pass

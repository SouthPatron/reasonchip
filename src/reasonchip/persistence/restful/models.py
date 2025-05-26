from __future__ import annotations

import uuid
import typing

from pydantic import (
    BaseModel,
    Field,
)


class RestfulModel(BaseModel):
    _endpoint: typing.ClassVar[str]

from __future__ import annotations

import typing
import sqlalchemy as sa

from sqlalchemy.ext.asyncio import AsyncEngine


class Rox:

    _instance: typing.Optional[Rox] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> Rox:
        if not cls._instance:
            raise RuntimeError("Rox instance is not initialized.")
        return cls._instance

    def __init__(
        self,
        engine: AsyncEngine,
        schema: str = "public",
    ):
        if Rox._initialized:
            return

        self._engine: AsyncEngine = engine
        self._schema: str = schema
        self._metadata: sa.MetaData = sa.MetaData(schema)

        Rox._initialized = True

    # ------------------------ PROPERTIES ------------------------------------

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def schema(self) -> str:
        return self._schema

    @property
    def metadata(self) -> sa.MetaData:
        return self._metadata

from __future__ import annotations

import typing
import sqlalchemy as sa

from pydantic import BaseModel, Field


from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_engine_from_config,
)


class RoxConfiguration(BaseModel):
    url: str = Field(default="sqlite+aiosqlite:///./rox.sqlite")
    pool_size: int = Field(default=1, ge=1)
    max_overflow: int = Field(default=10, ge=0)
    pool_recycle: int = Field(default=300, ge=0)
    pool_timeout: int = Field(default=30, ge=0)


class Rox:

    _instance: typing.Optional[Rox] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        configuration: RoxConfiguration,
    ):
        if Rox._initialized:
            return

        engine = async_engine_from_config(
            configuration.model_dump(),
            prefix="",
        )

        self._engine: AsyncEngine = engine
        self._metadata: sa.MetaData = sa.MetaData()

        Rox._initialized = True

    # ------------------------ PROPERTIES ------------------------------------

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def metadata(self) -> sa.MetaData:
        return self._metadata

    # ------------------------ METHODS ---------------------------------------

    @classmethod
    def get_instance(cls) -> Rox:
        if not cls._instance:
            raise RuntimeError("Rox instance is not initialized.")
        return cls._instance


class RoxSession:

    def __init__(self, rox: Rox):
        self._rox: Rox = rox
        self._session: typing.Optional[AsyncSession] = None

    async def __aenter__(self) -> AsyncSession:
        assert self._session is None
        self._session = AsyncSession(self._rox.engine)
        return await self._session.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert self._session is not None
        session = self._session
        self._session = None
        return await session.__aexit__(exc_type, exc_val, exc_tb)

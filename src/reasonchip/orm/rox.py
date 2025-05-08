import sqlalchemy as sa

from sqlalchemy.ext.asyncio import AsyncEngine


class Rox:

    def __init__(
        self,
        engine: AsyncEngine,
        schema: str = "public",
    ):
        self._engine: AsyncEngine = engine
        self._schema: str = schema
        self._metadata: sa.MetaData = sa.MetaData(schema)

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def schema(self) -> str:
        return self._schema

    @property
    def metadata(self) -> sa.MetaData:
        return self._metadata

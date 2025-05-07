import sqlalchemy as sa

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.schema import CreateSchema

from models import RoxModel, RoxRegistry


class Rox:

    def __init__(
        self,
        engine: AsyncEngine,
        schema: str = "public",
    ):
        self._engine: AsyncEngine = engine
        self._schema: str = schema
        self._metadata: sa.MetaData = sa.MetaData(schema)

    async def initialize(self) -> None:

        # Ensure schema
        async with self._engine.begin() as conn:
            await conn.execute(CreateSchema(self._schema, if_not_exists=True))

        # Create table definitions for all models
        await self._build_models()

        # Create the tables in the database
        async with self._engine.begin() as conn:
            await conn.run_sync(self._metadata.create_all)

    async def _build_models(self) -> None:
        for class_uuid, model in RoxRegistry._registry.items():

            tbl = sa.Table(
                model.Meta.table_name,
                self._metadata,
                sa.Column("id", sa.UUID, primary_key=True),
                sa.Column("version", sa.Integer, nullable=False),
                sa.Column("model", sa.JSON, nullable=False),
                sa.Column("last_updated_at", sa.DateTime, nullable=False),
                sa.Column("created_at", sa.DateTime, nullable=False),
            )

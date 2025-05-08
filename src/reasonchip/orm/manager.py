import typing
import uuid
import asyncio

import sqlalchemy as sa

from sqlalchemy.ext.asyncio import AsyncEngine

from dataclasses import dataclass, field

from .models import RoxModel
from .rox import Rox
from .models import RoxRegistry


from sqlalchemy.schema import CreateSchema


@dataclass
class RoxCachedModel:
    model: RoxModel
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class RoxManager:

    def __init__(
        self,
        rox: Rox,
    ):
        self._rox: Rox = rox
        self._lock: asyncio.Lock = asyncio.Lock()
        self._cache: typing.Dict[uuid.UUID, RoxCachedModel] = {}
        self._tables: typing.Dict[uuid.UUID, sa.Table] = {}

    # ------------------------ PROPERTIES ------------------------------------

    @property
    def engine(self) -> AsyncEngine:
        return self._rox.engine

    @property
    def metadata(self) -> sa.MetaData:
        return self._rox.metadata

    @property
    def schema(self) -> str:
        return self._rox.schema

    # ------------------------ LIFECYCLE -------------------------------------

    async def initialize(self) -> None:
        # Ensure schemas
        async with self.engine.begin() as conn:
            await conn.execute(CreateSchema(self.schema, if_not_exists=True))

        # Create table definitions for all models
        await self._build_model_tables()

        # Create the tables in the database
        async with self.engine.begin() as conn:
            await conn.run_sync(self.metadata.create_all)

    # ------------------------ DATABASE --------------------------------------

    async def load(
        self,
        model: typing.Type[RoxModel],
        oid: uuid.UUID,
    ) -> typing.Optional[RoxModel]:

        async with self._lock:
            if oid in self._cache:
                return self._cache[oid].model

            obj = await self._db_load(model, oid)
            if obj:
                self._cache[oid] = RoxCachedModel(model=obj)

            return obj

    async def save(
        self,
        obj: RoxModel,
    ):
        class_uuid = obj.__class__.Meta.class_uuid
        assert (
            class_uuid in self._tables
        ), f"Class UUID {class_uuid} ({obj.__class__}) not found in tables"

        tbl = self._tables[class_uuid]

        if obj.id is None:
            return await self._db_create(obj, tbl)

        async with self._rox.engine.begin() as session, session.begin():

            # Check if the object already exists
            stmt = sa.select(
                tbl.c.version,
                tbl.c.revision,
                tbl.c.model,
            ).where(tbl.c.id == obj.id)

            for row in await session.execute(stmt):
                # TODO: We need to do version management here
                version = row[0]
                revision = row[1]
                json_str = row[2]

                break

        # If we get here, we didn't find an existing object
        return self._db_create(obj, tbl)

    # ------------------------ LOADING ---------------------------------------

    async def _db_load(
        self,
        model: typing.Type[RoxModel],
        oid: uuid.UUID,
    ) -> typing.Optional[RoxModel]:

        class_uuid = model.Meta.class_uuid
        assert (
            class_uuid in self._tables
        ), f"Class UUID {class_uuid} ({model}) not found in tables"

        tbl = self._tables[class_uuid]

        async with self._rox.engine.begin() as session:

            stmt = sa.select(
                tbl.c.version,
                tbl.c.revision,
                tbl.c.model,
            ).where(tbl.c.id == oid)

            for row in await session.execute(stmt):

                # TODO: We need to do version management here

                version = row[0]
                revision = row[1]
                json_str = row[2]

                obj = model.model_validate_json(json_str)
                return obj

        return None

    # ------------------------ SAVING ----------------------------------------

    async def _db_create(
        self,
        obj: RoxModel,
        tbl: sa.Table,
    ):
        if obj.id is None:
            obj.id = uuid.uuid4()

    async def _db_update(
        self,
        obj: RoxModel,
        tbl: sa.Table,
    ):
        return

    # ------------------------ ADDITIONAL ------------------------------------

    async def _build_model_tables(self) -> None:
        for class_uuid, model in RoxRegistry._registry.items():
            self._tables[class_uuid] = sa.Table(
                model.Meta.table_name,
                self.metadata,
                sa.Column("id", sa.UUID, primary_key=True),
                sa.Column("version", sa.Integer, nullable=False),
                sa.Column("revision", sa.BigInteger, nullable=False, default=0),
                sa.Column("model", sa.JSON, nullable=False),
                sa.Column("last_updated_at", sa.DateTime, nullable=False),
                sa.Column("created_at", sa.DateTime, nullable=False),
            )

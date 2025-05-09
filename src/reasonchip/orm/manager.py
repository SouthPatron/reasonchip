from __future__ import annotations

import typing
import uuid
import asyncio
import json

import sqlalchemy as sa

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.schema import CreateSchema

from .models import RoxModel
from .rox import Rox

from .utils import pascal_to_snake


def custom_json_serializer(obj):

    if isinstance(obj, uuid.UUID):
        return str(obj)

    raise TypeError(f"Type {type(obj)} not serializable")


class RoxManager:

    _instance: typing.Optional[RoxManager] = None
    _initialized: bool = False

    # ------------------------ CONSTRUCTORS ----------------------------------

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._lock: asyncio.Lock = asyncio.Lock()
        self._seen: typing.Dict[str, typing.Dict[str, sa.sa.Table]] = {}
        self._rox: typing.Optional[Rox] = None

        self._initialized = True

    # ------------------------ PROPERTIES ------------------------------------

    @property
    def rox(self) -> Rox:
        if not self._rox:
            self._rox = Rox.get_instance()
        return self._rox

    # ------------------------ SUPPORT ---------------------------------------

    @classmethod
    def get_instance(cls) -> RoxManager:
        if not cls._instance:
            return cls()
        return cls._instance

    # ------------------------ DATABASE --------------------------------------

    async def load(
        self,
        model: typing.Type[RoxModel],
        oid: uuid.UUID,
    ) -> typing.Optional[RoxModel]:

        tbl = await self._fetch_table(model)

        async with self._lock:
            return await self._db_load(model, oid, tbl)

    async def save(
        self,
        model: typing.Type[RoxModel],
        oid: uuid.UUID,
        obj: typing.Dict[str, typing.Any],
        create: bool,
    ):
        rox = self.rox

        tbl = await self._fetch_table(model)

        async with AsyncSession(rox.engine) as session, session.begin():

            # Check if the object already exists
            if not create:
                stmt = (
                    sa.select(
                        tbl.c.version,
                        tbl.c.revision,
                        tbl.c.model,
                    )
                    .where(tbl.c.id == oid)
                    .with_for_update()
                )

                for row in await session.execute(stmt):
                    version, revision, json_str = row
                    return self._db_update(
                        session,
                        model,
                        oid,
                        obj,
                        tbl,
                        version,
                        revision,
                        json_str,
                    )

            # If we get here, it's a new object for sure
            return await self._db_create(
                session,
                model,
                obj,
                oid,
                tbl,
            )

    # ------------------------ LOADING ---------------------------------------

    async def _db_load(
        self,
        model: typing.Type[RoxModel],
        oid: uuid.UUID,
        tbl: sa.Table,
    ) -> typing.Optional[RoxModel]:

        rox = self.rox

        async with AsyncSession(rox.engine) as session:

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
        session: AsyncSession,
        model: typing.Type[RoxModel],
        obj: typing.Dict[str, typing.Any],
        oid: uuid.UUID,
        tbl: sa.Table,
    ):
        stmt = sa.insert(tbl).values(
            id=oid,
            version=1,
            revision=1,
            model=json.dumps(obj, default=custom_json_serializer),
        )

        result = await session.execute(stmt)
        if result.rowcount == 1:
            return

        raise RuntimeError(
            f"Failed to insert object {obj} into table {tbl.name}"
        )

    async def _db_update(
        self,
        session: AsyncSession,
        model: typing.Type[RoxModel],
        oid: uuid.UUID,
        obj: typing.Dict[str, typing.Any],
        tbl: sa.Table,
        version: int,
        revision: int,
        json_str: str,
    ):
        stmt = (
            sa.update(tbl)
            .where(tbl.c.id == oid)
            .values(
                revision=revision + 1,
                model=json.dumps(obj, default=custom_json_serializer),
            )
        )

        result = await session.execute(stmt)
        if result.rowcount == 1:
            return

        raise RuntimeError(
            f"Failed to update object {oid} into table {tbl.name}"
        )

    # ------------------------ SCHEMA CONTROL --------------------------------

    async def _fetch_table(
        self,
        model: typing.Type[RoxModel],
    ) -> sa.Table:

        rox = self.rox
        schema = rox.schema

        # Derive the table name from the class name
        table_name = pascal_to_snake(model.__name__)

        async with self._lock:

            # Check if we're aware of it.
            create_schema = schema not in self._seen
            if not create_schema:
                if table_name in self._seen[schema]:
                    return self._seen[schema][table_name]

            # We need to create something.
            async with self.rox.engine.begin() as conn:
                if create_schema:
                    await conn.execute(
                        CreateSchema(
                            schema,
                            if_not_exists=True,
                        )
                    )
                    self._seen[schema] = {}

                tbl = await self._build_table(
                    rox=rox,
                    table_name=table_name,
                )

                await conn.run_sync(tbl.create, checkfirst=True)
                self._seen[schema][table_name] = tbl

            return tbl

    async def _build_table(
        self,
        rox: Rox,
        table_name: str,
    ) -> sa.Table:
        return sa.Table(
            table_name,
            rox.metadata,
            sa.Column("id", sa.UUID, primary_key=True),
            sa.Column("version", sa.Integer, nullable=False),
            sa.Column("revision", sa.BigInteger, nullable=False, default=0),
            sa.Column("model", sa.JSON, nullable=False),
            sa.Column(
                "last_updated_at",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

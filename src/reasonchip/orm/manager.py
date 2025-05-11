from __future__ import annotations

import typing
import uuid
import asyncio
import json

import sqlalchemy as sa

from sqlalchemy.schema import CreateSchema
from sqlalchemy.ext.asyncio import AsyncSession, AsyncConnection

from .rox import Rox
from .utils import pascal_to_snake


ResultType = typing.Optional[
    typing.Tuple[int, int, typing.Dict[str, typing.Any]]
]
UpdateCallbackType = typing.Callable[
    [ResultType, typing.Dict[str, typing.Any]],
    typing.Awaitable[ResultType],
]


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

    # ------------------------ CRUD ------------------------------------------

    async def create(
        self,
        session: AsyncSession,
        model_name: str,
        schema: str,
        oid: uuid.UUID,
        version: int,
        revision: int,
        obj: typing.Dict[str, typing.Any],
    ):

        tbl = await self._fetch_table(session, schema, model_name)

        stmt = sa.insert(tbl).values(
            id=oid,
            version=version,
            revision=revision,
            model=json.dumps(obj, default=custom_json_serializer),
        )

        result = await session.execute(stmt)
        if result.rowcount == 1:
            return

        raise RuntimeError(
            f"Failed to insert object {obj} into table {tbl.name}"
        )

    async def load(
        self,
        session: AsyncSession,
        schema: str,
        model_name: str,
        oid: uuid.UUID,
    ) -> ResultType:

        tbl = await self._fetch_table(session, schema, model_name)

        stmt = sa.select(
            tbl.c.version,
            tbl.c.revision,
            tbl.c.model,
        ).where(tbl.c.id == oid)

        result = await session.execute(stmt)

        row = result.first()
        if not row:
            return None

        version = row[0]
        revision = row[1]
        json_str = row[2]
        return version, revision, json.loads(json_str)

    async def update(
        self,
        session: AsyncSession,
        schema: str,
        model_name: str,
        oid: uuid.UUID,
        callback: UpdateCallbackType,
        obj: typing.Dict[str, typing.Any],
    ) -> ResultType:

        tbl = await self._fetch_table(session, schema, model_name)

        stmt = (
            sa.select(
                tbl.c.version,
                tbl.c.revision,
                tbl.c.model,
            )
            .where(tbl.c.id == oid)
            .with_for_update()
        )

        result = await session.execute(stmt)

        row = result.first()

        params = (row[0], row[1], json.loads(row[2])) if row else None

        # Call the callback to get the new object
        rc = await callback(params, obj)
        if not rc:
            return None

        json_str = json.dumps(rc[2], default=custom_json_serializer)

        # Update or create depending on find
        if params:
            stmt = (
                sa.update(tbl)
                .where(tbl.c.id == oid)
                .values(
                    version=rc[0],
                    revision=rc[1],
                    model=json_str,
                )
            )
        else:
            stmt = sa.insert(tbl).values(
                id=oid,
                version=rc[0],
                revision=1,
                model=json_str,
            )

        result = await session.execute(stmt)
        if result.rowcount == 1:
            return rc

        raise RuntimeError(
            f"Failed to update object {oid} into table {tbl.name}"
        )

    async def delete(
        self,
        session: AsyncSession,
        schema: str,
        model_name: str,
        oid: uuid.UUID,
    ) -> bool:

        tbl = await self._fetch_table(session, schema, model_name)

        stmt = sa.delete(tbl).where(tbl.c.id == oid)
        result = await session.execute(stmt)
        return result.rowcount == 1

    # ------------------------ SCHEMA CONTROL --------------------------------

    async def _fetch_table(
        self,
        session: AsyncSession,
        schema: str,
        model_name: str,
    ) -> sa.Table:

        rox = self.rox
        metadata = rox.metadata

        # Derive the table name from the class name
        table_name = pascal_to_snake(model_name)

        async with self._lock:

            # Check if we're aware of it.
            create_schema = schema not in self._seen
            if not create_schema:
                if table_name in self._seen[schema]:
                    return self._seen[schema][table_name]

            # We need a direct connection.
            conn = await session.connection()

            # Make sure the schema exists along with rox tables
            if create_schema:
                await conn.execute(CreateSchema(schema, if_not_exists=True))
                rox_tables = await self._build_rox_tables(
                    conn,
                    metadata,
                    schema,
                )
                self._seen[schema] = rox_tables

            # Ensure actual table exists
            tbl = await self._build_table(
                metadata=metadata,
                table_name=table_name,
            )

            await conn.run_sync(tbl.create, checkfirst=True)
            self._seen[schema][table_name] = tbl

            return tbl

    async def _build_table(
        self,
        metadata: sa.MetaData,
        table_name: str,
    ) -> sa.Table:
        return sa.Table(
            table_name,
            metadata,
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

    async def _build_rox_tables(
        self,
        conn: AsyncConnection,
        metadata: sa.MetaData,
        schema: str,
    ) -> typing.Dict[str, sa.Table]:

        rc = {}

        # Make sure we have an entity table
        tbl = await self._build_entity_table(metadata, schema)
        await conn.run_sync(tbl.create, checkfirst=True)
        rc["rox_entity"] = tbl

        # Make sure we have a changelog table
        tbl = await self._build_changelog_table(metadata, schema)
        await conn.run_sync(tbl.create, checkfirst=True)
        rc["rox_changelog"] = tbl

        # Make sure we have an association table
        tbl = await self._build_association_table(metadata, schema)
        await conn.run_sync(tbl.create, checkfirst=True)
        rc["rox_association"] = tbl

        return rc

    async def _build_entity_table(
        self,
        metadata: sa.MetaData,
        schema: str,
    ) -> sa.Table:
        return sa.Table(
            "rox_entity",
            metadata,
            sa.Column("id", sa.UUID, primary_key=True),
            sa.Column("model_name", sa.String(255), nullable=False, index=True),
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
            schema=schema,
        )

    async def _build_changelog_table(
        self,
        metadata: sa.MetaData,
        schema: str,
    ) -> sa.Table:
        return sa.Table(
            "rox_changelog",
            metadata,
            sa.Column("id", sa.UUID, primary_key=True),
            sa.Column(
                "obj_id",
                sa.UUID,
                sa.ForeignKey("rox_entity.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("version", sa.Integer, nullable=False),
            sa.Column("revision", sa.BigInteger, nullable=False, default=0),
            sa.Column("patch", sa.JSON, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.now(),
            ),
            schema=schema,
        )

    async def _build_association_table(
        self,
        metadata: sa.MetaData,
        schema: str,
    ) -> sa.Table:
        return sa.Table(
            "rox_association",
            metadata,
            sa.Column("id", sa.UUID, primary_key=True),
            sa.Column(
                "parent_id",
                sa.UUID,
                sa.ForeignKey("rox_entity.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "child_id",
                sa.UUID,
                sa.ForeignKey("rox_entity.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.now(),
            ),
            schema=schema,
        )

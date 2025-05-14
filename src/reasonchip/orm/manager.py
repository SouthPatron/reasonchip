from __future__ import annotations

import typing
import uuid
import asyncio
import json

import diff_match_patch as dmp_module

import sqlalchemy as sa

from sqlalchemy.schema import CreateSchema
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncConnection,
)

from dataclasses import dataclass

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


@dataclass
class RoxAssociation:
    child_schema: str
    child_id: uuid.UUID


ROX_ENTITY = "rox_entity"
ROX_CHANGELOG = "rox_changelog"
ROX_ASSOCIATION = "rox_association"


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
        changelog: bool,
    ):
        json_str = json.dumps(obj, default=custom_json_serializer)

        tbl = await self._fetch_table(session, schema, model_name)
        stmt = sa.insert(tbl).values(
            id=oid,
            version=version,
            revision=revision,
            model=json_str,
        )

        # Create the entity
        result = await session.execute(stmt)
        if result.rowcount != 1:
            raise RuntimeError(
                f"Failed to insert object {obj} into table {tbl.name}"
            )

        # Register the entity
        if not await self.register_entity(session, schema, model_name, oid):
            raise RuntimeError(
                f"Failed to register entity {oid} into table {tbl.name}"
            )

        if not changelog:
            return

        # Record the changelog
        success = await self.create_changelog_entry(
            session,
            schema,
            oid,
            version,
            revision,
            "",
            json_str,
        )
        if not success:
            raise RuntimeError(
                f"Failed to create changelog entry for {oid} into table {tbl.name}"
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
        changelog: bool,
    ) -> ResultType:

        # Get the entity from the database
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

        if row:
            old_json_str = row[2]
            params = (row[0], row[1], json.loads(old_json_str))
        else:
            old_json_str = ""
            params = None

        # Call the callback to get the new object
        rc = await callback(params, obj)
        if not rc:
            return None

        new_version = rc[0]
        new_revision = rc[1]
        json_str = json.dumps(rc[2], default=custom_json_serializer)

        # Update because it already exists
        if params:
            stmt = (
                sa.update(tbl)
                .where(tbl.c.id == oid)
                .values(
                    version=new_version,
                    revision=new_revision,
                    model=json_str,
                )
            )

            result = await session.execute(stmt)
            if result.rowcount != 1:
                raise RuntimeError(
                    f"Failed to update object {oid} into table {tbl.name}"
                )

            # Touch entity
            if not await self.touch_entity(session, schema, oid):
                raise RuntimeError(
                    f"Failed to touch entity {oid} into table {tbl.name}"
                )
        else:
            # Create because it doesn't exist
            stmt = sa.insert(tbl).values(
                id=oid,
                version=new_version,
                revision=new_revision,
                model=json_str,
            )
            result = await session.execute(stmt)
            if result.rowcount != 1:
                raise RuntimeError(
                    f"Failed to update (via insert) object {oid} into table {tbl.name}"
                )

            # Register the entity
            result = await self.register_entity(
                session,
                schema,
                model_name,
                oid,
            )
            if not result:
                raise RuntimeError(
                    f"Failed to register entity {oid} into table {tbl.name}"
                )

        if not changelog:
            return rc

        # Record the changelog
        success = await self.create_changelog_entry(
            session,
            schema,
            oid,
            new_version,
            new_revision,
            old_json_str,
            json_str,
        )
        if not success:
            raise RuntimeError(
                f"Failed to create changelog entry for {oid} into table {tbl.name}"
            )

        return rc

    async def delete(
        self,
        session: AsyncSession,
        schema: str,
        model_name: str,
        oid: uuid.UUID,
    ) -> bool:

        # Try delete the entity first to trigger any foreign key constraints
        rc = await self.deregister_entity(
            session,
            schema,
            oid,
        )
        if not rc:
            return False

        # Seems we're okay. Delete the object.
        tbl = await self._fetch_table(session, schema, model_name)

        stmt = sa.delete(tbl).where(tbl.c.id == oid)
        await session.execute(stmt)

        # It doesn't matter if the actual object didn't exist. It matters
        # that it's been deregistered as an entity.
        return True

    # ------------------------ ENTITY CONTROL --------------------------------

    async def register_entity(
        self,
        session: AsyncSession,
        schema: str,
        model_name: str,
        oid: uuid.UUID,
    ) -> bool:

        tbl = await self._fetch_table(session, schema, ROX_ENTITY)

        stmt = sa.insert(tbl).values(
            id=oid,
            model_name=model_name,
        )
        result = await session.execute(stmt)
        return result.rowcount == 1

    async def touch_entity(
        self,
        session: AsyncSession,
        schema: str,
        oid: uuid.UUID,
    ) -> bool:

        tbl = await self._fetch_table(session, schema, ROX_ENTITY)

        stmt = (
            sa.update(tbl)
            .where(tbl.c.id == oid)
            .values(
                last_updated_at=sa.func.now(),
            )
        )

        result = await session.execute(stmt)
        return result.rowcount == 1

    async def deregister_entity(
        self,
        session: AsyncSession,
        schema: str,
        oid: uuid.UUID,
    ) -> bool:

        tbl = await self._fetch_table(session, schema, ROX_ENTITY)

        stmt = sa.delete(tbl).where(tbl.c.id == oid)
        result = await session.execute(stmt)
        return result.rowcount == 1

    async def set_entity_associations(
        self,
        session: AsyncSession,
        schema: str,
        oid: uuid.UUID,
        associations: typing.List[RoxAssociation],
    ):

        tbl = await self._fetch_table(session, schema, ROX_ASSOCIATION)

        # Delete all existing associations
        stmt = sa.delete(tbl).where(tbl.c.parent_id == oid)
        await session.execute(stmt)

        # Create new associations
        for assoc in associations:
            stmt = sa.insert(tbl).values(
                id=uuid.uuid4(),
                parent_id=oid,
                child_schema=assoc.child_schema,
                child_id=assoc.child_id,
            )
            await session.execute(stmt)

        return True

    # ------------------------ CHANGELOG CONTROL -----------------------------

    async def create_changelog_entry(
        self,
        session: AsyncSession,
        schema: str,
        oid: uuid.UUID,
        version: int,
        revision: int,
        old_json: str,
        new_json: str,
    ) -> bool:

        # First we generate the patch difference
        dmp = dmp_module.diff_match_patch()

        # Upwards
        diffs_up = dmp.diff_main(old_json, new_json)
        diffs_down = dmp.diff_main(new_json, old_json)

        dmp.diff_cleanupSemantic(diffs_up)
        dmp.diff_cleanupSemantic(diffs_down)

        patches_up = dmp.patch_make(old_json, diffs_up)
        patches_down = dmp.patch_make(new_json, diffs_down)

        patch_up = dmp.patch_toText(patches_up)
        patch_down = dmp.patch_toText(patches_down)

        # Now we record it.
        tbl = await self._fetch_table(session, schema, ROX_CHANGELOG)

        stmt = sa.insert(tbl).values(
            id=uuid.uuid4(),
            oid=oid,
            version=version,
            revision=revision,
            patch_up=patch_up,
            patch_down=patch_down,
        )

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

        # Determine schema support
        engine = session.get_bind()
        assert isinstance(engine, sa.Engine)

        use_schema = engine.dialect.name != "sqlite"

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
                rox_tables = await self._build_rox_tables(
                    conn,
                    metadata,
                    schema,
                    use_schema,
                )
                self._seen[schema] = rox_tables

            # Ensure actual table exists
            tbl = await self._build_table(
                metadata=metadata,
                schema=schema,
                table_name=table_name,
                use_schema=use_schema,
            )

            await conn.run_sync(tbl.create, checkfirst=True)
            self._seen[schema][table_name] = tbl

            return tbl

    async def _build_table(
        self,
        metadata: sa.MetaData,
        schema: str,
        table_name: str,
        use_schema: bool,
    ) -> sa.Table:

        if use_schema:
            tname = table_name
        else:
            tname = f"{schema}_{table_name}"

        return sa.Table(
            tname,
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
            schema=schema if use_schema else None,
        )

    async def _build_rox_tables(
        self,
        conn: AsyncConnection,
        metadata: sa.MetaData,
        schema: str,
        use_schema: bool,
    ) -> typing.Dict[str, sa.Table]:

        rc = {}

        # Create the schema if supported and it doesn't exist
        if use_schema:
            await conn.execute(CreateSchema(schema, if_not_exists=True))

        # Make sure we have an entity table
        tbl = await self._build_entity_table(metadata, schema, use_schema)
        await conn.run_sync(tbl.create, checkfirst=True)
        rc[ROX_ENTITY] = tbl

        # Make sure we have a changelog table
        tbl = await self._build_changelog_table(metadata, schema, use_schema)
        await conn.run_sync(tbl.create, checkfirst=True)
        rc[ROX_CHANGELOG] = tbl

        # Make sure we have an association table
        tbl = await self._build_association_table(metadata, schema, use_schema)
        await conn.run_sync(tbl.create, checkfirst=True)
        rc[ROX_ASSOCIATION] = tbl

        print(f"Created Rox tables in schema {schema}: {rc}")

        return rc

    async def _build_entity_table(
        self,
        metadata: sa.MetaData,
        schema: str,
        use_schema: bool,
    ) -> sa.Table:

        if use_schema:
            tname = ROX_ENTITY
        else:
            tname = f"{schema}_{ROX_ENTITY}"

        return sa.Table(
            tname,
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
            schema=schema if use_schema else None,
        )

    async def _build_changelog_table(
        self,
        metadata: sa.MetaData,
        schema: str,
        use_schema: bool,
    ) -> sa.Table:

        if use_schema:
            tname = ROX_CHANGELOG
            fkey = f"{schema}.{ROX_ENTITY}.id"
        else:
            tname = f"{schema}_{ROX_CHANGELOG}"
            fkey = f"{schema}_{ROX_ENTITY}.id"

        return sa.Table(
            tname,
            metadata,
            sa.Column("id", sa.UUID, primary_key=True),
            sa.Column(
                "oid",
                sa.UUID,
                sa.ForeignKey(fkey, ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("version", sa.Integer, nullable=False),
            sa.Column("revision", sa.BigInteger, nullable=False, default=0),
            sa.Column("patch_up", sa.Text, nullable=False),
            sa.Column("patch_down", sa.Text, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.now(),
            ),
            schema=schema if use_schema else None,
        )

    async def _build_association_table(
        self,
        metadata: sa.MetaData,
        schema: str,
        use_schema: bool,
    ) -> sa.Table:

        if use_schema:
            tname = ROX_ASSOCIATION
            fkey = f"{schema}.{ROX_ENTITY}.id"
        else:
            tname = f"{schema}_{ROX_ASSOCIATION}"
            fkey = f"{schema}_{ROX_ENTITY}.id"

        return sa.Table(
            tname,
            metadata,
            sa.Column("id", sa.UUID, primary_key=True),
            sa.Column(
                "parent_id",
                sa.UUID,
                sa.ForeignKey(fkey, ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "child_schema",
                sa.String(255),
                nullable=False,
            ),
            sa.Column(
                "child_id",
                sa.UUID,
                sa.ForeignKey(fkey, ondelete="RESTRICT"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.now(),
            ),
            schema=schema if use_schema else None,
        )

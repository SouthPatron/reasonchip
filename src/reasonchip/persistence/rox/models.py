from __future__ import annotations

import uuid
import typing

import sqlalchemy as sa

from pydantic import (
    BaseModel,
    Field,
)

from .rox import Rox, RoxSession
from .manager import (
    RoxManager,
    RoxAssociation,
    ResultType,
)

RX = typing.TypeVar("RX", bound="RoxModel")


class RoxModel(BaseModel):

    # Common field for all Rox models
    id: typing.Optional[uuid.UUID] = None

    _revision: int = 1
    _version: typing.ClassVar[int] = 1
    _schema: typing.ClassVar[str] = "public"
    _changelog: typing.ClassVar[bool] = False

    # ------------ CONSTRUCTORS ----------------------------------------------

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dirty: bool = False

    # ------------ ORM METHODS -----------------------------------------------

    @classmethod
    async def load(
        cls: typing.Type[RX],
        oid: uuid.UUID,
        session: typing.Optional[sa.AsyncSession] = None,
    ) -> typing.Optional[RX]:

        # Retrieve a session
        if session is None:
            rox = Rox.get_instance()
            async with RoxSession(rox) as session:
                return await cls.load(oid=oid, session=session)

        # Perform the load operation
        obj = await cls._recursive_load(
            session=session,
            model=cls,
            oid=oid,
        )
        if obj is None:
            print(f"Object with id {oid} not found.")
            return None

        obj._dirty = False
        return obj

    async def save(
        self,
        session: typing.Optional[sa.AsyncSession] = None,
    ) -> uuid.UUID:

        # Retrieve a session
        if session is None:
            rox = Rox.get_instance()
            async with RoxSession(rox) as session, session.begin():
                return await self.save(session=session)

        # Perform the save operation
        associations: typing.List[RoxAssociation] = []
        await self._recursive_save_and_replace(
            session=session,
            obj=self,
            depth=0,
            associations=associations,
        )

        assert self.id is not None

        # Update all associations
        await self.manager().set_entity_associations(
            session=session,
            schema=self._schema,
            oid=self.id,
            associations=associations,
        )

        self._dirty = False
        return self.id

    async def delete(
        self,
        session: typing.Optional[sa.AsyncSession] = None,
    ) -> bool:
        assert self.id is not None

        # Retrieve a session
        if session is None:
            rox = Rox.get_instance()
            async with RoxSession(rox) as session, session.begin():
                return await self.delete(session=session)

        # Perform the delete operation
        return await self.manager().delete(
            session=session,
            schema=self._schema,
            model_name=self.__class__.__name__,
            oid=self.id,
        )

    # ------------ SUPPORT METHODS -------------------------------------------

    _manager: typing.ClassVar[typing.Optional[RoxManager]] = None

    @classmethod
    def manager(cls) -> RoxManager:
        if not cls._manager:
            cls._manager = RoxManager.get_instance()
        return cls._manager

    # ------------ SAVING METHODS --------------------------------------------

    async def _recursive_save_and_replace(
        self,
        session: sa.AsyncSession,
        obj: typing.Any,
        depth: int,
        associations: typing.List[RoxAssociation],
    ):
        """
        NOTE:

        This will iterate over the current object into all the fields. It will
        delve into lists and dicts.

        If it finds another RoxModel, it will:

        1. Call save on that model so it can do it's thing.
        2. Replace the storage reference with a dict that contains the
            reference to the other reference.

        It also keeps track of all associations at this current level (ie:
        not any sub-RoxModels) within the provided parameter.
        """

        if isinstance(obj, RoxModel):
            # We are not saving ourselves, we're saving a child.
            if depth > 0:
                new_id = await obj.save(session=session)

                # Keep track of associations
                associations.append(
                    RoxAssociation(
                        child_schema=obj._schema,
                        child_id=new_id,
                    )
                )

                return {
                    "__ref__": new_id,
                    "__rox__": obj.__class__.__name__,
                    "__schema__": obj.__class__._schema,
                }

            # We are saving ourselves
            assert obj == self

            # Determine if we are creating or updating
            create = obj.id is None
            if obj.id is None:
                obj.id = uuid.uuid4()  # NOTE: This will mark us dirty
                obj._revision = 1

            # Iterate over the fields of the object
            result = {}
            for name in obj.__class__.model_fields.keys():
                value = getattr(obj, name)
                result[name] = await self._recursive_save_and_replace(
                    session=session,
                    obj=value,
                    depth=depth + 1,
                    associations=associations,
                )

            # Save the object to the database here
            if obj.is_dirty():
                if create:
                    await self.manager().create(
                        session=session,
                        model_name=obj.__class__.__name__,
                        schema=obj._schema,
                        version=obj._version,
                        revision=obj._revision,
                        oid=obj.id,
                        obj=result,
                        changelog=obj._changelog,
                    )
                else:
                    await self.manager().update(
                        session=session,
                        schema=obj._schema,
                        model_name=obj.__class__.__name__,
                        oid=obj.id,
                        callback=self._update_collision_check,
                        obj=result,
                        changelog=obj._changelog,
                    )

            # Return the reference
            return {
                "__ref__": obj.id,
                "__rox__": obj.__class__.__name__,
                "__schema__": obj.__class__._schema,
            }

        elif isinstance(obj, list):
            return [
                await self._recursive_save_and_replace(
                    session=session,
                    obj=i,
                    depth=depth + 1,
                    associations=associations,
                )
                for i in obj
            ]

        elif isinstance(obj, dict):
            return {
                k: await self._recursive_save_and_replace(
                    session=session,
                    obj=v,
                    depth=depth + 1,
                    associations=associations,
                )
                for k, v in obj.items()
            }

        else:
            return obj

    async def _update_collision_check(
        self,
        existing_row: ResultType,
        obj: typing.Dict[str, typing.Any],
    ) -> ResultType:

        if not existing_row:
            return (self._version, self._revision, obj)

        version = existing_row[0]
        revision = existing_row[1]
        old_obj = existing_row[2]

        # NOTE:
        # 1. It's okay for versions to be different.
        # 2. Revisions should be equal, or else someone has touched it before us.

        if revision != (self._revision - 1):
            # TODO: Handle merging of the object
            print(
                f"Revision mismatch: {obj} {revision} != {self._revision - 1}"
            )
            raise ValueError(
                f"Revision mismatch: {revision} != {self._revision - 1}"
            )

        rc = (self._version, self._revision, obj)
        return rc

    # ------------ LOADING METHODS -------------------------------------------

    @classmethod
    async def _recursive_load(
        cls: typing.Type[RX],
        session: sa.AsyncSession,
        model: typing.Type[RX],
        oid: uuid.UUID,
    ) -> typing.Optional[RX]:

        row = await cls.manager().load(
            session=session,
            schema=model._schema,
            model_name=model.__name__,
            oid=oid,
        )
        if row is None:
            return None

        version = row[0]
        revision = row[1]
        obj = row[2]

        if version != cls._version:
            # TODO: Handle migration of object
            raise ValueError(f"Version mismatch: {version} != {cls._version}")

        # New object
        new_obj = await cls._unflatten_value(session=session, value=obj)

        rc = model.model_validate(new_obj)
        rc._revision = revision
        return rc

    @classmethod
    async def _unflatten_value(
        cls,
        session: sa.AsyncSession,
        value: typing.Any,
    ) -> typing.Optional[typing.Any]:

        if isinstance(value, dict):
            # Reference ...
            if "__ref__" in value and "__rox__" in value:
                ref = uuid.UUID(value["__ref__"])
                ref_model_name = value["__rox__"]
                ref_schema = value["__schema__"]

                key_name = f"{ref_schema}.{ref_model_name}"

                if key_name not in cls._registry:
                    raise ValueError(
                        f"Model {key_name} not registered but it's needed to load from the DB."
                    )

                sub_model = cls._registry[key_name]
                return await sub_model.load(oid=ref, session=session)

            # Not a reference
            for name, val in value.items():
                value[name] = await cls._unflatten_value(session, val)

            return value

        if isinstance(value, list):
            return [await cls._unflatten_value(session, x) for x in value]

        return value

    # ------------ DIRTY MANAGEMENT ------------------------------------------

    def __setattr__(self, name, value):
        super().__setattr__(name, value)

        if name in ["_dirty"]:
            return

        if self._dirty == False:
            self._dirty = True
            if name not in ["_revision"]:
                self._revision = self._revision + 1

    def is_dirty(self) -> bool:
        return self._dirty

    # ------------ FACTORY REGISTRY ------------------------------------------

    _registry: typing.ClassVar[typing.Dict[str, typing.Type[RoxModel]]] = {}

    def __init_subclass__(cls):
        super().__init_subclass__()

        key_name = f"{cls._schema}.{cls.__name__}"

        if key_name in cls._registry:
            raise ValueError(
                f"Class {key_name} already registered in the registry."
            )

        cls._registry[key_name] = cls

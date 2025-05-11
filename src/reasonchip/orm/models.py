from __future__ import annotations

import uuid
import typing

from pydantic import (
    BaseModel,
    Field,
)


class RoxModel(BaseModel):

    # Common field for all Rox models
    id: typing.Optional[uuid.UUID] = None

    _revision: int = 1
    _version: typing.ClassVar[int] = 1

    # ------------ ORM METHODS -----------------------------------------------

    @classmethod
    async def load(cls, oid: uuid.UUID) -> typing.Optional[RoxModel]:
        obj = await cls._recursive_load(cls, oid)
        print(
            f"Loaded {cls.__name__} with id {oid} and revision {obj._revision}"
        )
        return obj

    async def save(self) -> uuid.UUID:
        await self._recursive_save_and_replace(self, 0)
        assert self.id is not None
        return self.id

    async def delete(self) -> bool:
        assert self.id is not None

        return await self.manager().delete(
            model=self.__class__,
            oid=self.id,
        )

    # ------------ SUPPORT METHODS -------------------------------------------

    _manager: typing.ClassVar[typing.Optional["RoxManager"]] = None

    @classmethod
    def manager(cls) -> "RoxManager":
        if not cls._manager:
            from .manager import RoxManager

            cls._manager = RoxManager.get_instance()
        return cls._manager

    # ------------ SAVING METHODS --------------------------------------------

    async def _recursive_save_and_replace(
        self,
        obj: typing.Any,
        depth: int,
    ):
        if isinstance(obj, RoxModel):
            # We are not saving ourselves, we're saving a child.
            if depth > 0:
                new_id = await obj.save()
                return {
                    "__ref__": new_id,
                    "__rox__": obj.__class__.__name__,
                }

            # We are saving ourselves
            create = obj.id is None
            if obj.id is None:
                self._revision = 1
                obj.id = uuid.uuid4()

            result = {}
            for name in obj.__class__.model_fields.keys():
                value = getattr(obj, name)
                result[name] = await self._recursive_save_and_replace(
                    obj=value,
                    depth=depth + 1,
                )

            # Save the object to the database here
            if create:
                await self.manager().create(
                    model=obj.__class__,
                    oid=obj.id,
                    obj=result,
                )
            else:
                await self.manager().update(
                    model=obj.__class__,
                    oid=obj.id,
                    callback=self._update_collision_check,
                    obj=result,
                )

            # Return the reference
            return {
                "__ref__": obj.id,
                "__rox__": obj.__class__.__name__,
            }

        elif isinstance(obj, list):
            return [
                await self._recursive_save_and_replace(
                    obj=i,
                    depth=depth + 1,
                )
                for i in obj
            ]

        elif isinstance(obj, dict):
            return {
                k: await self._recursive_save_and_replace(
                    obj=v,
                    depth=depth + 1,
                )
                for k, v in obj.items()
            }

        else:
            return obj

    async def _update_collision_check(
        self,
        existing_row: typing.Optional[
            typing.Tuple[int, int, typing.Dict[str, typing.Any]]
        ],
        obj: typing.Dict[str, typing.Any],
    ) -> typing.Optional[typing.Tuple[int, int, typing.Dict[str, typing.Any]]]:

        if not existing_row:
            return (self._version, self._revision, obj)

        version = existing_row[0]
        revision = existing_row[1]
        old_obj = existing_row[2]

        print(f"Comparing DB {revision} == OBJ {self._revision}")

        if version != self._version:
            # TODO: Handle migration of object.
            raise ValueError(f"Version mismatch: {version} != {self._version}")

        if revision != self._revision:
            # TODO: Handle merging of the object
            print(f"Revision mismatch: {obj} {revision} != {self._revision}")
            raise ValueError(
                f"Revision mismatch: {revision} != {self._revision}"
            )

        else:
            self._revision += 1

        rc = (self._version, self._revision, obj)
        return rc

    # ------------ LOADING METHODS -------------------------------------------

    @classmethod
    async def _recursive_load(
        cls,
        model: typing.Type[RoxModel],
        oid: uuid.UUID,
    ) -> typing.Optional[RoxModel]:

        row = await cls.manager().load(model=model, oid=oid)
        if row is None:
            return None

        version = row[0]
        revision = row[1]
        obj = row[2]

        if version != cls._version:
            # TODO: Handle migration of object
            raise ValueError(f"Version mismatch: {version} != {cls._version}")

        # New object
        new_obj = await cls._unflatten_value(obj)

        rc = model.model_validate(new_obj)
        rc._revision = revision
        return rc

    @classmethod
    async def _unflatten_value(
        cls,
        value: typing.Any,
    ) -> typing.Optional[typing.Any]:

        if isinstance(value, dict):
            # Reference ...
            if "__ref__" in value and "__rox__" in value:
                ref = uuid.UUID(value["__ref__"])
                ref_model_name = value["__rox__"]

                if ref_model_name not in cls._registry:
                    raise ValueError(
                        f"Model {ref_model_name} not registered but it's needed to load from the DB."
                    )

                sub_model = cls._registry[ref_model_name]
                return await sub_model.load(ref)

            # Not a reference
            for name, val in value.items():
                value[name] = await cls._unflatten_value(val)

            return value

        if isinstance(value, list):
            return [await cls._unflatten_value(x) for x in value]

        return value

    # ------------ FACTORY REGISTRY ------------------------------------------

    _registry: typing.ClassVar[typing.Dict[str, typing.Type[RoxModel]]] = {}

    def __init_subclass__(cls):
        super().__init_subclass__()

        if cls.__name__ in cls._registry:
            raise ValueError(
                f"Class {cls.__name__} already registered in the registry."
            )

        cls._registry[cls.__name__] = cls

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

    async def save(self) -> uuid.UUID:
        await self._recursive_save_and_replace(self)
        assert self.id is not None
        return self.id

    async def delete(self) -> bool:
        assert self.id is not None

        return await self.manager().delete(
            model=self.__class__,
            oid=self.id,
        )

    # ------------ ORM METHODS -----------------------------------------------

    _manager: typing.ClassVar[typing.Optional["RoxManager"]] = None

    @classmethod
    def manager(cls) -> "RoxManager":
        if not cls._manager:
            from .manager import RoxManager

            cls._manager = RoxManager.get_instance()
        return cls._manager

    async def _recursive_save_and_replace(self, obj: typing.Any):
        if isinstance(obj, RoxModel):
            create = obj.id is None

            if obj.id is None:
                obj.id = uuid.uuid4()

            result = {}
            for name in obj.__class__.model_fields.keys():
                value = getattr(obj, name)
                result[name] = await self._recursive_save_and_replace(value)

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
            return [await self._recursive_save_and_replace(i) for i in obj]

        elif isinstance(obj, dict):
            return {
                k: await self._recursive_save_and_replace(v)
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
            return (self._version, 1, obj)

        version = existing_row[0]
        revision = existing_row[1]
        old_obj = existing_row[2]

        if version != self._version:
            # TODO: Handle migration of object.
            raise ValueError(f"Version mismatch: {version} != {self._version}")

        if revision != self._revision:
            # TODO: Handle merging of the object
            raise ValueError(
                f"Revision mismatch: {revision} != {self._revision}"
            )

        rc = (self._version, self._revision + 1, obj)
        return rc

import uuid
import typing

from pydantic import (
    BaseModel,
    Field,
)


class RoxModel(BaseModel):

    # Common field for all Rox models
    id: typing.Optional[uuid.UUID] = None
    version: int = Field(default=1, frozen=True)

    @property
    def manager(self) -> "RoxManager":
        from .manager import RoxManager

        return RoxManager.get_instance()

    async def save(self) -> uuid.UUID:
        rc = await self._recursive_save_and_replace(self)
        assert self.id is not None
        return self.id

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
            await self.manager.save(
                model=obj.__class__,
                oid=obj.id,
                obj=result,
                create=create,
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

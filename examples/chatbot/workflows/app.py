import typing

from reasonchip.core.engine.engine import EngineContext


async def entry(context: EngineContext) -> typing.Any:
    print("Hello, world!")
    return True

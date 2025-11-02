import typing

from reasonchip import EngineContext


def simple_call(context: EngineContext) -> typing.Any:
    return "OTHER: Hello from simple call!"


async def simple_async_call(context: EngineContext) -> typing.Any:
    return "OTHER: Hello from simple async call!"


async def entry(context: EngineContext) -> typing.Any:
    print("OTHER: Testing calling simple app...")

    pathways = [
        ".other.simple_call",
        ".other.simple_async_call",
    ]

    for p in pathways:
        rc = await context.branch(p)
        print(f"OTHER: Result from {p}: {rc}")

    return True

import typing

from reasonchip import EngineContext


def simple_call(context: EngineContext) -> typing.Any:
    return "Hello from simple call!"


async def simple_async_call(context: EngineContext) -> typing.Any:
    return "Hello from simple async call!"


async def entry(context: EngineContext) -> typing.Any:
    print("Testing calling simple app...")

    pathways = [
        ".app.simple_call",
        ".app.simple_async_call",
        ".other",
        ".other.simple_call",
        ".other.simple_async_call",
    ]

    for p in pathways:
        print(f"Calling pathway: {p}")
        rc = await context.branch(p)
        print(f"Result: {rc}")

    return "fin."

import typing
import asyncio
import uuid

from dataclasses import dataclass, field

from ...protocol import SocketPacket, PacketType


@dataclass
class ClientSession:
    connection_id: uuid.UUID = field(default_factory=uuid.uuid4)
    death_signal: asyncio.Event = field(default_factory=asyncio.Event)
    outgoing_queue: asyncio.Queue[SocketPacket] = field(default_factory=asyncio.Queue)



NewConnectionType = typing.Callable[[ClientSession], typing.Awaitable[None]]
ReadCallback = typing.Callable[[ClientSession, SocketPacket], typing.Awaitable[None]]
DisconnectCallback = typing.Callable[[ClientSession], typing.Awaitable[None]]


@dataclass
class CallbackHooks:
    new_connection: NewConnectionType
    read_callback: ReadCallback
    disconnect_callback: DisconnectCallback



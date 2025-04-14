import typing
import uuid

from abc import ABC, abstractmethod

from ..protocol import SocketPacket


NewConnectionCallbackType = typing.Callable[
    ["ServerTransport", uuid.UUID], typing.Awaitable[None]
]
ReadCallbackType = typing.Callable[
    [uuid.UUID, SocketPacket], typing.Awaitable[None]
]
ClosedConnectionCallbackType = typing.Callable[
    [uuid.UUID], typing.Awaitable[None]
]


class ServerTransport(ABC):

    @abstractmethod
    async def start_server(
        self,
        new_connection_callback: NewConnectionCallbackType,
        read_callback: ReadCallbackType,
        closed_connection_callback: ClosedConnectionCallbackType,
    ) -> bool: ...

    @abstractmethod
    async def stop_server(self) -> bool: ...

    @abstractmethod
    async def send_packet(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ) -> bool: ...

    @abstractmethod
    async def close_connection(
        self,
        connection_id: uuid.UUID,
    ) -> bool: ...

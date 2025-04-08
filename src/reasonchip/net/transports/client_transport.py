import typing
import uuid

from abc import ABC, abstractmethod

from ..protocol import SocketPacket

ReadCallbackType = typing.Callable[[uuid.UUID, typing.Optional[SocketPacket]], typing.Awaitable[None]]


class ClientTransport(ABC):


    @abstractmethod
    async def connect(
        self,
        callback: ReadCallbackType,
        cookie: typing.Optional[uuid.UUID] = None,
    ) -> bool: ...


    @abstractmethod
    async def disconnect(self): ...


    @abstractmethod
    async def send_packet(self, packet: SocketPacket) -> bool: ...



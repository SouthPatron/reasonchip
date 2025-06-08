from httpx import AsyncClient

from abc import ABC, abstractmethod


class AuthHandler(ABC):

    @abstractmethod
    async def login(self, client: AsyncClient): ...

    @abstractmethod
    async def logout(self, client: AsyncClient): ...

    @abstractmethod
    async def on_request(self, client: AsyncClient): ...

    @abstractmethod
    async def on_forbidden(self, client: AsyncClient): ...

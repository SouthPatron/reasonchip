import typing
import asyncio

from httpx import AsyncClient, Response

from .auth_handler import AuthHandler


class DjangoRestfulTokenAuth(AuthHandler):

    def __init__(
        self,
        login_url: str,
        username: str,
        password: str,
    ):
        super().__init__()
        self._login_url = login_url
        self._username = username
        self._password = password
        self._token: typing.Optional[str] = None
        self._lock = asyncio.Lock()

    async def login(self, client: AsyncClient):
        try:
            resp: Response = await client.post(
                self._login_url,
                json={
                    "username": self._username,
                    "password": self._password,
                },
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Login failed: {resp.status_code} {resp.text}"
                )

            data = resp.json()
            self._token = data["token"]

        except Exception as e:
            raise RuntimeError(f"Login error: {e}") from e

    async def logout(self, client: AsyncClient):
        self._token = None  # Clear the token before logout

    async def on_request(self, client: AsyncClient):
        async with self._lock:
            # If client doesn't already have the token, fetch it.
            if not self._token:
                await self.login(client)

            # Set the Authorization header with the token.
            client.headers["Authorization"] = f"Token {self._token}"

    async def on_forbidden(self, client: AsyncClient):
        async with self._lock:
            await self.login(client)
            client.headers["Authorization"] = f"Token {self._token}"

import typing
import asyncio
import logging

from aio_pika import (
    connect_robust,
    Message,
    DeliveryMode,
    ExchangeType,
)
from aio_pika.abc import (
    AbstractRobustConnection,
    AbstractRobustChannel,
    AbstractRobustExchange,
)


log = logging.getLogger("reasonchip.net.amqp_client")


class AmqpClient:

    def __init__(self):
        # Implementation
        self._amqp_url: typing.Optional[str] = None
        self._exchange_name: typing.Optional[str] = None

        # Connection information
        self._connection: typing.Optional[AbstractRobustConnection] = None
        self._channel: typing.Optional[AbstractRobustChannel] = None
        self._exchange: typing.Optional[AbstractRobustExchange] = None

    # ------------------ LIFECYCLE -------------------------------------------

    async def connect(
        self,
        amqp_url: str,
        exchange_name: str,
    ) -> bool:
        try:
            log.debug(
                f"Connecting to AMQP broker: '{amqp_url}' and exchange '{exchange_name}'"
            )

            self._amqp_url = amqp_url
            self._exchange_name = exchange_name

            # Create the connection
            self._connection = await connect_robust(self._amqp_url)

            # NOTE: this call actually returns a coroutine. Remove ignore to
            # check if they've fixed the return type. It's aio-pika's fault.
            self._channel = await self._connection.channel()  # type: ignore
            assert self._channel is not None

            # Declare the exchange
            self._exchange = await self._channel.declare_exchange(
                self._exchange_name,
                ExchangeType.TOPIC,
                durable=True,
            )

            log.debug(f"Connected to AMQP client: '{self._exchange_name}'")
            return True

        except Exception:
            log.exception("Failed to connect to the AMQP broker")
            return False

    async def disconnect(self):

        self._exchange = None

        if self._channel:
            await self._channel.close()
            self._channel = None

        if self._connection:
            await self._connection.close()
            self._connection = None

        log.debug("Disconnected from AMQP broker.")

    async def send_message(
        self,
        topic: str,
        message: bytes,
        timeout: typing.Optional[float] = None,
    ) -> bool:
        assert self._exchange is not None

        try:
            await self._exchange.publish(
                Message(message, delivery_mode=DeliveryMode.PERSISTENT),
                routing_key=topic,
                timeout=timeout,
            )
            return True

        except asyncio.TimeoutError:
            log.warning("Timeout while sending message to AMQP broker")
            return False

        except StopAsyncIteration:
            log.warning("AMQP broker connection closed while sending message")
            return False

        except Exception:
            log.exception("Failed to send message to AMQP broker")
            return False

import typing
import asyncio
import logging

from .simple_task import SimpleTask

from aio_pika import (
    connect_robust,
    Message,
    DeliveryMode,
    ExchangeType,
)
from aio_pika.abc import (
    AbstractRobustConnection,
    AbstractRobustChannel,
)


log = logging.getLogger("reasonchip.core.net.amqp_producer")


class AmqpProducer(SimpleTask):

    def __init__(self):
        super().__init__(name="AmqpProducer")

        # Implementation
        self._connection: typing.Optional[AbstractRobustConnection] = None
        self._amqp_url: typing.Optional[str] = None
        self._exchange_name: typing.Optional[str] = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._loop_interval: float = 1

    # ------------------ LIFECYCLE -------------------------------------------

    def initialize(
        self,
        amqp_url: str,
        exchange_name: str,
        loop_interval: float = 1,
    ) -> bool:
        try:
            log.info("Initializing AMQP producer")
            self._amqp_url = amqp_url
            self._exchange_name = exchange_name
            self._loop_interval = loop_interval
            return True

        except Exception:
            log.exception("Failed to initialize AMQP producer")
            return False

    def shutdown(self) -> bool:
        assert self._connection is not None

        self._connection = None
        log.info("Shutdown AMQP producer complete")
        return True

    async def impl(self) -> None:
        log.info("Starting AMQP producer loop")

        channel: typing.Optional[AbstractRobustChannel] = None

        assert self._connection is None
        assert self._amqp_url
        assert self._exchange_name

        try:
            self._connection = await connect_robust(
                self._amqp_url,
            )

            # NOTE: this call actually returns a coroutine. Remove ignore to
            # check if they've fixed the return type. It's aio-pika's fault.
            channel = await self._connection.channel()  # type: ignore
            assert channel is not None

            exchange = await channel.declare_exchange(
                self._exchange_name,
                ExchangeType.TOPIC,
                durable=True,
            )

            while self.keep_running():
                try:
                    topic, msg = await asyncio.wait_for(
                        self._message_queue.get(), timeout=self._loop_interval
                    )
                    await exchange.publish(
                        Message(msg, delivery_mode=DeliveryMode.PERSISTENT),
                        routing_key=topic,
                    )

                except asyncio.TimeoutError:
                    continue
                except StopAsyncIteration:
                    break

        except Exception:
            log.exception("Unexpected error in AMQP producer")

        finally:
            if channel:
                await channel.close()
            if self._connection:
                await self._connection.close()
                self._connection = None

            log.info("Exiting AMQP producer loop")

    async def send_message(self, topic: str, message: bytes) -> None:
        assert self._connection is not None
        await self._message_queue.put((topic, message))

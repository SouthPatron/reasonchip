import typing
import logging
import asyncio
import enum

from .simple_task import SimpleTask

from aio_pika import connect_robust, ExchangeType
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractRobustChannel,
    AbstractRobustConnection,
    AbstractRobustQueue,
)

log = logging.getLogger("reasonchip.net.amqp_consumer")


class AMQPCallbackResp(enum.Enum):
    ACK = 1
    REJECT = 2
    REQUEUE = 3


AMQPConsumerCallback = typing.Callable[
    [bytes], typing.Awaitable[AMQPCallbackResp]
]


class AmqpConsumer(SimpleTask):

    def __init__(
        self,
        callback: AMQPConsumerCallback,
    ):
        super().__init__(name="AmqpConsumer")

        # Implementation
        self._callback: AMQPConsumerCallback = callback

        self._amqp_url: typing.Optional[str] = None
        self._queue_name: typing.Optional[str] = None
        self._exchange_name: typing.Optional[str] = None
        self._routing_key: typing.Optional[str] = None
        self._loop_interval: float = 1

    # ------------------ LIFECYCLE -------------------------------------------

    def initialize(
        self,
        amqp_url: str,
        queue_name: str,
        exchange_name: str = "",
        routing_key: str = "",
        loop_interval: float = 1,
    ) -> bool:
        try:
            log.info("Initializing AMQP consumer")
            self._amqp_url = amqp_url
            self._queue_name = queue_name
            self._exchange_name = exchange_name
            self._routing_key = routing_key
            self._loop_interval = loop_interval
            return True

        except Exception:
            log.exception("Failed to initialize AMQP consumer")
            return False

    def shutdown(self) -> bool:
        log.info("Shutdown AMQP consumer complete")
        return True

    async def impl(self) -> None:
        log.info("Starting AMQP consumer loop")

        connection: typing.Optional[AbstractRobustConnection] = None
        channel: typing.Optional[AbstractRobustChannel] = None
        queue: typing.Optional[AbstractRobustQueue] = None

        assert self._amqp_url
        assert self._queue_name
        assert self._exchange_name
        assert self._routing_key

        try:
            connection = await connect_robust(self._amqp_url)

            # NOTE: this call actually returns a coroutine. Remove ignore to
            # check if they've fixed the return type. It's aio-pika's fault.
            channel = await connection.channel()  # type: ignore
            assert channel is not None

            queue = await channel.declare_queue(
                self._queue_name,
                durable=True,
            )
            exchange = await channel.declare_exchange(
                self._exchange_name,
                ExchangeType.TOPIC,
                durable=True,
            )
            await queue.bind(
                exchange,
                routing_key=self._routing_key,
            )

            async def message_handler(msg: AbstractIncomingMessage):
                rc: AMQPCallbackResp = await self._callback(msg.body)
                if rc == AMQPCallbackResp.ACK:
                    await msg.ack()
                elif rc == AMQPCallbackResp.REJECT:
                    await msg.reject(requeue=False)
                elif rc == AMQPCallbackResp.REQUEUE:
                    await msg.reject(requeue=True)
                else:
                    assert False, "Invalid AMQP callback response"

            consumer_tag = await queue.consume(message_handler)

            # Main loop
            while self.keep_running():
                await asyncio.sleep(self._loop_interval)

            await queue.cancel(consumer_tag)

        except Exception:
            log.exception("Unexpected error in AMQP Consumer")
            raise

        finally:
            if channel:
                await channel.close()
            if connection:
                await connection.close()

            log.info("Exiting AMQP Consumer loop")

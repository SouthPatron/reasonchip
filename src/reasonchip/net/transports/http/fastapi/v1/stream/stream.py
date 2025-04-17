# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import asyncio
import logging

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse

from ....common import ClientSession, SocketPacket, PacketType

log = logging.getLogger(__name__)

router = APIRouter()


# ************* Dependency injections ****************************************

from ... import di

# ************* Models *******************************************************


# ************* Routes *******************************************************


@router.post("/stream")
async def stream(
    request: Request,
    req: SocketPacket,
    callbacks: di.CallbackHooks = Depends(di.get_callbacks),
) -> StreamingResponse:
    """
    Handle streaming connections from clients.

    Registers new connection, sends initial packet, then streams packets back asynchronously.

    :param request: The incoming FastAPI request.
    :param req: The initial socket packet from the client.
    :param callbacks: Dependency injection callbacks for connection lifecycle.

    :return: A StreamingResponse yielding encoded socket packets.
    """
    session = ClientSession()

    # Register connection
    await callbacks.new_connection(session)

    # Send through the initial packet
    await callbacks.read_callback(session, req)

    async def log_stream() -> typing.AsyncGenerator[bytes, None]:
        """
        Async generator that yields packets to stream until session death or result packet.

        :yield: Encoded JSON string of SocketPacket objects.
        """
        try:
            # Create tasks to wait for session death and outgoing packets
            t_die = asyncio.create_task(session.death_signal.wait())
            t_reader = asyncio.create_task(session.outgoing_queue.get())

            wl = [t_die, t_reader]

            while wl:

                done, _ = await asyncio.wait(
                    wl,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if t_die in done:
                    wl.remove(t_die)
                    if t_reader:
                        t_reader.cancel()
                    t_die = None

                if t_reader in done:
                    assert t_reader
                    wl.remove(t_reader)

                    if not t_reader.cancelled():

                        pkt = t_reader.result()
                        assert isinstance(pkt, SocketPacket)

                        json_str = pkt.model_dump_json() + "\n"
                        yield json_str.encode("utf-8")

                        if pkt.packet_type != PacketType.RESULT:
                            # We keep doing this until we get a result
                            t_reader = asyncio.create_task(
                                session.outgoing_queue.get()
                            )
                            wl.append(t_reader)

                        else:
                            # If this is the end, we need finish this request.
                            session.death_signal.set()
                            t_reader = None

                    else:
                        t_reader = None

        except Exception as e:
            log.exception("Exception in log_stream")

        finally:
            # This one is gone
            await callbacks.disconnect_callback(session)

    return StreamingResponse(
        log_stream(), media_type="application/octet-stream"
    )

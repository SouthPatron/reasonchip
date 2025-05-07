# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import uuid
import logging
import json

from ..protocol import (
    SocketPacket,
    PacketType,
    ResultCode,
)

from .multiplexor import Multiplexor
from .client import Client

from . import exceptions as rex


class Api:

    def __init__(self, multiplexor: Multiplexor) -> None:
        self._multiplexor = multiplexor

    async def run_pipeline(
        self,
        pipeline: str,
        variables: typing.Any = None,
        cookie: typing.Optional[uuid.UUID] = None,
        detached: bool = False,
    ) -> typing.Any:

        async with Client(
            multiplexor=self._multiplexor,
            cookie=cookie,
        ) as client:

            logging.debug(
                f"Request to run pipeline: [{client.get_cookie()}] {pipeline}"
            )

            json_variables = json.dumps(variables) if variables else None

            req = SocketPacket(
                packet_type=PacketType.RUN,
                pipeline=pipeline,
                variables=json_variables,
                detach=detached,
            )

            # Send the request to the broker
            logging.debug("Dispatching request")
            rc = await client.send_packet(req)
            if not rc:
                logging.debug("Failed to dispatch request")
                raise rex.ConnectionException("Failed to send packet to broker")

            if detached:
                logging.debug("Detached job, no response expected")
                return None

            # Wait for the all the response packets
            logging.debug("Waiting for responses")
            while resp := await client.receive_packet():

                # No timeout, means we will always get a response
                assert resp != None

                logging.debug(f"Received packet: {resp.packet_type}")

                # The only thing left is a RESULT
                assert resp.packet_type == PacketType.RESULT

                # Raise any exception cleanly.
                if resp.rc != ResultCode.OK:

                    exc_class = None

                    if resp.rc == ResultCode.BAD_PACKET:
                        exc_class = rex.BadPacketException

                    elif resp.rc == ResultCode.UNSUPPORTED_PACKET_TYPE:
                        exc_class = rex.UnsupportedPacketTypeException

                    elif resp.rc == ResultCode.NO_CAPACITY:
                        exc_class = rex.NoCapacityException

                    elif resp.rc == ResultCode.COOKIE_NOT_FOUND:
                        exc_class = rex.CookieNotFoundException

                    elif resp.rc == ResultCode.COOKIE_COLLISION:
                        exc_class = rex.CookieCollisionException

                    elif resp.rc == ResultCode.WORKER_WENT_AWAY:
                        exc_class = rex.WorkerWentAwayException

                    elif resp.rc == ResultCode.BROKER_WENT_AWAY:
                        exc_class = rex.BrokerWentAwayException

                    elif resp.rc == ResultCode.PROCESSOR_EXCEPTION:
                        exc_class = rex.ProcessorException

                    elif resp.rc == ResultCode.EXCEPTION:
                        exc_class = rex.GeneralException

                    assert exc_class is not None

                    raise exc_class(
                        cookie=resp.cookie,
                        rc=resp.rc,
                        error=resp.error,
                        stacktrace=resp.stacktrace,
                    )

                # Return the response
                assert resp.rc == ResultCode.OK

                if resp.result is None:
                    return None

                return json.loads(resp.result)

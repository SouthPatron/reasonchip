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


class Api:

    def __init__(self, multiplexor: Multiplexor) -> None:
        self._multiplexor = multiplexor

    async def run_pipeline(
        self,
        pipeline: str,
        variables: typing.Any = None,
        cookie: typing.Optional[uuid.UUID] = None,
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
            )

            logging.debug("Dispatching request")
            rc = await client.send_packet(req)
            if not rc:
                logging.debug("Failed to dispatch request")
                raise ConnectionError("Lost connection to engine client")

            logging.debug("Waiting for all the responses")
            while resp := await client.receive_packet():
                if not resp:
                    logging.debug("Lost connection to engine client")
                    raise ConnectionError("Lost connection to engine client")

                logging.debug(f"Received packet: {resp.packet_type}")

                # This is in response to a cancel
                if resp.packet_type == PacketType.CANCEL:
                    logging.debug("Job was confirmed as cancelled")
                    if resp.result != ResultCode.CANCELLED:
                        logging.warning(f"Job cancellation failed. [{resp.rc}]")
                    break

                # This is the end of the job
                if resp.packet_type == PacketType.RESULT:
                    print(f"Received response: {resp}")
                    break

                # If the callback returns False, then we need to cancel the running job
                if rc == False:
                    req = SocketPacket(packet_type=PacketType.CANCEL)

                    logging.debug("Dispatching request")
                    rc = await client.send_packet(req)
                    if not rc:
                        logging.debug("Failed to dispatch request")
                        raise ConnectionError(
                            "Lost connection to engine client"
                        )

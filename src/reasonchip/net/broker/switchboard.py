import typing
import uuid
import asyncio
import logging

from collections import defaultdict

from dataclasses import dataclass

from ..protocol import (
    SocketPacket,
    PacketType,
    ResultCode,
)


@dataclass
class Route:
    route_id: uuid.UUID
    client_id: uuid.UUID
    connection_id: uuid.UUID
    client_gone: bool = False


@dataclass
class ClientPayload:
    connection_id: uuid.UUID
    packet: SocketPacket


WriterCallbackType = typing.Callable[[uuid.UUID, SocketPacket], typing.Awaitable[bool]]


class Switchboard:

    def __init__(
        self,
        writer_callback: WriterCallbackType,
    ):
        # Writer callback
        self._writer_callback: WriterCallbackType = writer_callback

        # Routes and connections
        self._lock: asyncio.Lock = asyncio.Lock()
        self._available: typing.List[uuid.UUID] = []

        self._routes: typing.Dict[uuid.UUID, Route] = {}
        self._routes_by_client: typing.Dict[uuid.UUID, typing.List[Route]] = defaultdict(list)
        self._routes_by_worker: typing.Dict[uuid.UUID, typing.List[Route]] = defaultdict(list)


    # --------------------- PAYLOAD HANDLING ----------------------------------

    async def eliminate_client(self, connection_id: uuid.UUID):
        """
        NOTE: The workers are still busy doing things so we don't cancel them.
        """
        async with self._lock:
            # Mark existing routes as orphans
            if connection_id in self._routes_by_client:
                routes = self._routes_by_client[connection_id]
                for r in routes:
                    r.client_gone = True

            await self.print_status()


    async def eliminate_worker(self, connection_id: uuid.UUID):
        """
        NOTE: We have to inform all clients that the connection went away and
        then clean up the routes.
        """

        async with self._lock:

            # Inform all clients that the connection went away
            if connection_id in self._routes_by_worker:

                # For every open route, inform the client
                routes = self._routes_by_worker[connection_id]
                for r in routes:
                    # Remove from the route from the global routes
                    self._routes.pop(r.route_id)

                    await self._writer_callback(r.client_id, SocketPacket(
                        packet_type = PacketType.RESULT,
                        cookie = r.route_id,
                        rc = ResultCode.WORKER_WENT_AWAY,
                        error = "The worker connection went away",
                    ))

                    # Remove the route for the client
                    self._routes_by_client[r.client_id].remove(r)
                    # If it has no more routes, delete knowledge about the client

                    if not self._routes_by_client[r.client_id]:
                        self._routes_by_client.pop(r.client_id)

                # Finally remove the worker route entry
                self._routes_by_worker.pop(connection_id)


            # Now we purge the available connections of the worker
            self._available = [
                c
                for c in self._available
                if c != connection_id
            ]

            # Tell the world
            await self.print_status()


    # --------------------- PAYLOAD HANDLING ----------------------------------

    async def client_payload(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ):
        handlers = {
            PacketType.RUN: self._cl_run,
            PacketType.CANCEL: self._cl_passthru,
        }
        payload = ClientPayload(connection_id = connection_id, packet = packet)
        handler = handlers.get(packet.packet_type, self._unsupported_packet)
        await handler(payload)


    async def worker_payload(
        self,
        connection_id: uuid.UUID,
        packet: SocketPacket,
    ):
        handlers = {
            PacketType.REGISTER: self._wk_register,
            PacketType.RESULT: self._wk_result,
        }
        payload = ClientPayload(connection_id = connection_id, packet = packet)
        handler = handlers.get(payload.packet.packet_type, self._unsupported_packet)
        await handler(payload)


    # --------------------- COMMON --------------------------------------------

    async def _respond(
        self,
        payload: ClientPayload,
        rc: ResultCode,
        error: str,
    ):
        # Log the error
        logging.error(
            f"Sending error response [{payload.connection_id}] [{payload.packet.packet_type}] [{rc}] [{error}]"
        )

        # Get the packet
        pkt = payload.packet

        # Create the packet
        resp = SocketPacket(
            packet_type = PacketType.RESULT,
            cookie = pkt.cookie,
            rc = rc,
            error = error,
        )

        # And send it back
        await self._writer_callback(payload.connection_id, resp)


    async def _unsupported_packet(self, payload: ClientPayload):
        return await self._respond(
            payload = payload,
            rc = ResultCode.UNSUPPORTED_PACKET_TYPE,
            error = "Packet type not supported on this client",
        )


    async def _bad_packet(self, payload: ClientPayload, reason: str):
        return await self._respond(
            payload = payload,
            rc = ResultCode.BAD_PACKET,
            error = reason,
        )


    # --------------------- CLIENTS -------------------------------------------


    async def _cl_run(self, payload: ClientPayload):

        # Get the packet
        pkt = payload.packet

        # Sanity checks
        if not pkt.cookie:
            return await self._bad_packet(payload, "Missing cookie")

        if not pkt.pipeline:
            return await self._bad_packet(payload, "Missing pipeline")

        # Get some information
        cookie = pkt.cookie

        async with self._lock:

            # Make sure the cookie doesn't already exist in the routes
            if cookie in self._routes:
                return await self._respond(
                    payload = payload,
                    rc = ResultCode.COOKIE_COLLISION,
                    error = "Already in use",
                )

            # Make sure there are available connections
            if not self._available:
                return await self._respond(
                    payload = payload,
                    rc = ResultCode.NO_CAPACITY,
                    error = "No capacity available",
                )

            # Create the Route and keep track of it
            conn = self._available.pop()
            route = Route(
                route_id = cookie,
                client_id = payload.connection_id,
                connection_id = conn,
            )
            self._routes[cookie] = route
            self._routes_by_client[payload.connection_id].append(route)
            self._routes_by_worker[conn].append(route)

            # Log what happened
            logging.info(f"CLIENT RUN: cookie=[{cookie}] pipeline=[{pkt.pipeline}] client=[{payload.connection_id}] connection=[{conn}]")

            # Send through to the worker
            await self._writer_callback(conn, pkt)


    async def _cl_passthru(self, payload: ClientPayload):

        # Get the packet
        pkt = payload.packet

        # Sanity checks
        if not pkt.cookie:
            return await self._bad_packet(payload, "Missing cookie")

        # Get some information
        cookie = pkt.cookie

        async with self._lock:

            # Make sure the cookie exists in the routes
            if cookie not in self._routes:
                return await self._respond(
                    payload = payload,
                    rc = ResultCode.COOKIE_NOT_FOUND,
                    error = "No such cookie",
                )

            # Get the route
            route = self._routes[cookie]

            # Send through to the worker
            await self._writer_callback(route.connection_id, pkt)


    # --------------------- WORKERS -------------------------------------------



    async def _wk_register(self, payload: ClientPayload):

        # Make sure the worker has capacity
        pkt = payload.packet
        assert pkt.capacity and pkt.capacity >= 1

        # Now register and make available the new connections
        async with self._lock:
            for _ in range(pkt.capacity):
                self._available.append(payload.connection_id)

            # Tell the world
            await self.print_status()


    async def _wk_result(self, payload: ClientPayload):

        # Get the packet
        pkt = payload.packet

        # Sanity checks
        if not pkt.cookie:
            return await self._bad_packet(payload, "Missing cookie")

        # Get some information
        cookie = pkt.cookie

        async with self._lock:

            # Make sure the cookie exists in the routes
            assert cookie in self._routes

            # Get the route
            route = self._routes.pop(cookie)

            # Remove from the client list
            self._routes_by_client[route.client_id].remove(route)
            if not self._routes_by_client[route.client_id]:
                self._routes_by_client.pop(route.client_id)

            # Remove from the worker list
            self._routes_by_worker[route.connection_id].remove(route)
            if not self._routes_by_worker[route.connection_id]:
                self._routes_by_worker.pop(route.connection_id)

            # Send through to the worker
            if route.client_gone:
                logging.warning(f"Client gone [{route.client_id}]")
            else:
                await self._writer_callback(route.client_id, pkt)

            # Log what happened
            logging.info(f"WORKER RESULT: cookie=[{cookie}] rc=[{pkt.rc}] error=[{pkt.error}] client=[{route.client_id}] connection=[{route.connection_id}]")

            # Return the connection to the available pool
            self._available.append(route.connection_id)


    # --------------------- CLEANUP -------------------------------------------

    async def print_status(self):
        avail = len(self._available)
        routes = len(self._routes)
        rbw = len(self._routes_by_worker)
        rbc = len(self._routes_by_client)

        msg = f"STATS: available [{avail}] | routes [{routes}] rbw [{rbw}] rbc [{rbc}]"
        logging.info(msg)


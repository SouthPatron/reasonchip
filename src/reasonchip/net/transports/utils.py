# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import re
import ssl
import enum
import socket
import logging

from dataclasses import dataclass

from .ssl_options import SSLClientOptions, SSLServerOptions

from .client_transport import ClientTransport
from .server_transport import ServerTransport

from .tcp_client import TcpClient
from .socket_client import SocketClient
from .grpc_client import GrpcClient
from .http_client import HttpClient

from .tcp_server import TcpServer
from .socket_server import SocketServer
from .grpc_server import GrpcServer
from .http_server import HttpServer


from ..protocol import (
    DEFAULT_CLIENT_PORT_TCP,
    DEFAULT_CLIENT_PORT_GRPC,
    DEFAULT_CLIENT_PORT_HTTP,
    DEFAULT_WORKER_PORT_TCP,
    DEFAULT_WORKER_PORT_GRPC,
)

log = logging.getLogger(__name__)


class ClientType(enum.IntEnum):
    WORKER = enum.auto()
    CLIENT = enum.auto()


def get_port(scheme: str, client_type: ClientType) -> int:
    """
    Get the default port number for a given scheme and client type.

    :param scheme: The scheme (tcp, grpc, http).
    :param client_type: The type of client (worker or client).

    :return: The default port number.
    """

    if client_type == ClientType.CLIENT:
        if scheme == "tcp":
            log.debug(f"Using TCP client port: {DEFAULT_CLIENT_PORT_TCP}")
            return DEFAULT_CLIENT_PORT_TCP

        if scheme == "grpc":
            log.debug(f"Using gRPC client port: {DEFAULT_CLIENT_PORT_GRPC}")
            return DEFAULT_CLIENT_PORT_GRPC

        if scheme == "http":
            log.debug(f"Using HTTP client port: {DEFAULT_CLIENT_PORT_HTTP}")
            return DEFAULT_CLIENT_PORT_HTTP

    if client_type == ClientType.WORKER:
        if scheme == "tcp":
            log.debug(f"Using TCP worker port: {DEFAULT_WORKER_PORT_TCP}")
            return DEFAULT_WORKER_PORT_TCP

        if scheme == "grpc":
            log.debug(f"Using gRPC worker port: {DEFAULT_WORKER_PORT_GRPC}")
            return DEFAULT_WORKER_PORT_GRPC

    log.error(
        f"Not sure which port to use for scheme '{scheme}' and client_type '{client_type}'"
    )
    assert True, "Not sure which port to use"
    return 0


# ------------------- SUPPORT CLASSES ----------------------------------------


@dataclass
class ConnectionTarget:
    raw_target: str
    host: typing.Optional[str] = None
    port: typing.Optional[int] = None
    is_ipv6: bool = False
    family: typing.Optional[int] = None

    def __post_init__(self):
        """
        Parse the raw target string to extract host, port, and family info.

        :return: None
        """
        # IPv6 address with optional port: [::1]:5000
        ipv6_match = re.match(
            r"^\[(?P<ip>[0-9a-fA-F:]+)\](?::(?P<port>\d+))?$", self.raw_target
        )
        if ipv6_match:
            self.host = ipv6_match.group("ip")
            self.port = (
                int(ipv6_match.group("port"))
                if ipv6_match.group("port")
                else None
            )
            self.is_ipv6 = True
            self.family = socket.AF_INET6
            log.debug(f"Parsed IPv6 target: host={self.host}, port={self.port}")
            return

        # IPv4 or hostname with optional port
        if ":" in self.raw_target:
            host_part, port_part = self.raw_target.rsplit(":", 1)
            self.host = host_part
            self.family = socket.AF_INET
            try:
                self.port = int(port_part)
                log.debug(
                    f"Parsed target with port: host={self.host}, port={self.port}"
                )
            except ValueError:
                log.error(f"Invalid port number in target: {self.raw_target}")
                raise ValueError(
                    f"Invalid port number in target: {self.raw_target}"
                )
        else:
            self.host = self.raw_target
            self.port = None
            log.debug(f"Parsed target without port: host={self.host}")


@dataclass
class TransportOptions:
    scheme: str
    target: str

    @classmethod
    def from_args(cls, url: str) -> "TransportOptions":
        """
        Create a TransportOptions instance from command line arguments.

        :param url: The URL string to parse.

        :return: A TransportOptions instance.
        """
        pattern = re.compile(
            r"""
            ^
            (?P<scheme>grpc|tcp|http|socket)://           # Scheme
            (?P<target>
                (?:                                       # Start non-capturing group for target
                    \[[0-9a-fA-F:]+\](?::\d+)?            # IPv6 (with optional port)
                    |
                    \d{1,3}(?:\.\d{1,3}){3}(?::\d+)?      # IPv4 (with optional port)
                    |
                    [a-zA-Z0-9.-]+(?::\d+)?               # Hostname (with optional port)
                    |
                    /[^ ]+                                # Unix path
                )
            )
            /?$                                           # Trailing slash
        """,
            re.VERBOSE,
        )

        match = pattern.match(url)
        if not match:
            log.error(f"Invalid URL format: {url}")
            raise ValueError(f"Invalid URL format: {url}")

        log.debug(
            f"Parsed TransportOptions from url: scheme={match.group('scheme')}, target={match.group('target')}"
        )
        return TransportOptions(
            scheme=match.group("scheme"),
            target=match.group("target"),
        )


# ------------------- CLIENT CONNECTIONS -------------------------------------


def client_connection(
    addr: str,
    client_type: ClientType,
    ssl_client_options: typing.Optional[SSLClientOptions] = None,
    ssl_context: typing.Optional[ssl.SSLContext] = None,
) -> ClientTransport:
    """
    Create a client connection transport based on the address and client type.

    :param addr: The address string.
    :param client_type: The type of client.
    :param ssl_client_options: SSL options for the client (optional).
    :param ssl_context: SSL context for the client (optional).

    :return: An instance of ClientTransport.
    """

    parsed = TransportOptions.from_args(addr)
    default_port = get_port(parsed.scheme, client_type)

    if parsed.scheme == "tcp":
        ct = ConnectionTarget(parsed.target)
        log.info(f"Creating TcpClient to {ct.host}:{ct.port or default_port}")
        return TcpClient(
            host=ct.host,
            port=ct.port or default_port,
            ssl=ssl_context,
            family=socket.AF_INET6 if ct.is_ipv6 else socket.AF_INET,
        )

    elif parsed.scheme == "socket":
        log.info(f"Creating SocketClient to path {parsed.target}")
        return SocketClient(
            path=parsed.target,
            ssl=ssl_context,
        )

    elif parsed.scheme == "grpc":
        ct = ConnectionTarget(parsed.target)
        new_port = ct.port or default_port

        if ct.is_ipv6:
            new_target = f"[{ct.host}]:{new_port}"
        else:
            new_target = f"{ct.host}:{new_port}"

        log.info(f"Creating GrpcClient to target {new_target}")
        return GrpcClient(
            target=new_target,
            ssl_options=ssl_client_options,
        )

    elif parsed.scheme == "http":
        ct = ConnectionTarget(parsed.target)
        new_port = ct.port or default_port

        if ct.is_ipv6:
            new_target = f"[{ct.host}]:{new_port}"
        else:
            new_target = f"{ct.host}:{new_port}"

        log.info(f"Creating HttpClient to target {new_target}")
        return HttpClient(
            target=new_target,
            ssl_context=ssl_context,
        )

    log.error(f"Unknown scheme: {parsed.scheme}")
    raise ValueError(f"Unknown scheme: {parsed.scheme}")


def client_to_broker(
    addr: str,
    ssl_client_options: typing.Optional[SSLClientOptions] = None,
    ssl_context: typing.Optional[ssl.SSLContext] = None,
) -> ClientTransport:
    """
    Create a client transport connection to a broker.

    :param addr: The address string.
    :param ssl_client_options: SSL options for the client (optional).
    :param ssl_context: SSL context for the client (optional).

    :return: A ClientTransport instance for a client.
    """
    log.info(f"Creating client_to_broker connection to {addr}")
    return client_connection(
        addr,
        client_type=ClientType.CLIENT,
        ssl_client_options=ssl_client_options,
        ssl_context=ssl_context,
    )


def worker_to_broker(
    addr: str,
    ssl_client_options: typing.Optional[SSLClientOptions] = None,
    ssl_context: typing.Optional[ssl.SSLContext] = None,
) -> ClientTransport:
    """
    Create a worker transport connection to a broker.

    :param addr: The address string.
    :param ssl_client_options: SSL options for the worker (optional).
    :param ssl_context: SSL context for the worker (optional).

    :return: A ClientTransport instance for a worker.
    """
    log.info(f"Creating worker_to_broker connection to {addr}")
    return client_connection(
        addr,
        client_type=ClientType.WORKER,
        ssl_client_options=ssl_client_options,
        ssl_context=ssl_context,
    )


# ------------------- SERVER CONNECTIONS -------------------------------------


def server_connection(
    addr: str,
    client_type: ClientType,
    ssl_server_options: typing.Optional[SSLServerOptions] = None,
    ssl_context: typing.Optional[ssl.SSLContext] = None,
) -> ServerTransport:
    """
    Create a server transport connection based on the address and client type.

    :param addr: The address string.
    :param client_type: The type of client.
    :param ssl_server_options: SSL options for the server (optional).
    :param ssl_context: SSL context for the server (optional).

    :return: An instance of ServerTransport.
    """

    parsed = TransportOptions.from_args(addr)
    default_port = get_port(parsed.scheme, client_type)

    if parsed.scheme == "tcp":
        ct = ConnectionTarget(parsed.target)

        log.info(f"Creating TcpServer on {ct.host}:{ct.port or default_port}")
        return TcpServer(
            hosts=ct.host,
            port=ct.port or default_port,
            ssl=ssl_context,
            family=socket.AF_INET6 if ct.is_ipv6 else socket.AF_INET,
        )

    elif parsed.scheme == "socket":
        log.info(f"Creating SocketServer on path {parsed.target}")
        return SocketServer(
            path=parsed.target,
            ssl=ssl_context,
        )

    elif parsed.scheme == "grpc":
        ct = ConnectionTarget(parsed.target)
        new_port = ct.port or default_port

        if ct.is_ipv6:
            new_target = f"[{ct.host}]:{new_port}"
        else:
            new_target = f"{ct.host}:{new_port}"

        log.info(f"Creating GrpcServer on target {new_target}")
        return GrpcServer(
            host=new_target,
            ssl_options=ssl_server_options,
        )

    elif parsed.scheme == "http":
        ct = ConnectionTarget(parsed.target)
        new_port = ct.port or default_port

        if ct.is_ipv6:
            new_target = f"[{ct.host}]:{new_port}"
        else:
            new_target = f"{ct.host}:{new_port}"

        log.info(f"Creating HttpServer on target {new_target}")
        return HttpServer(
            host=new_target,
            ssl_options=ssl_server_options,
        )

    log.error(f"Unknown scheme: {parsed.scheme}")
    raise ValueError(f"Unknown scheme: {parsed.scheme}")


def broker_for_workers(
    addresses: typing.List[str],
    ssl_server_options: typing.Optional[SSLServerOptions] = None,
    ssl_context: typing.Optional[ssl.SSLContext] = None,
) -> typing.List[ServerTransport]:
    """
    Create server transports for workers based on a list of addresses.

    :param addresses: List of address strings.
    :param ssl_server_options: SSL options for the servers (optional).
    :param ssl_context: SSL context for the servers (optional).

    :return: List of ServerTransport instances.
    """
    rc = []
    for addr in addresses:
        log.info(f"Creating worker broker server connection for {addr}")
        rc.append(
            server_connection(
                addr,
                ClientType.WORKER,
                ssl_server_options,
                ssl_context,
            )
        )
    return rc


def broker_for_clients(
    addresses: typing.List[str],
    ssl_server_options: typing.Optional[SSLServerOptions] = None,
    ssl_context: typing.Optional[ssl.SSLContext] = None,
) -> typing.List[ServerTransport]:
    """
    Create server transports for clients based on a list of addresses.

    :param addresses: List of address strings.
    :param ssl_server_options: SSL options for the servers (optional).
    :param ssl_context: SSL context for the servers (optional).

    :return: List of ServerTransport instances.
    """
    rc = []
    for addr in addresses:
        log.info(f"Creating client broker server connection for {addr}")
        rc.append(
            server_connection(
                addr,
                ClientType.CLIENT,
                ssl_server_options,
                ssl_context,
            )
        )
    return rc

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import re
import ssl
import enum
import socket

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


class ClientType(enum.IntEnum):
    WORKER = enum.auto()
    CLIENT = enum.auto()


def get_port(scheme: str, client_type: ClientType) -> int:

    if client_type == ClientType.CLIENT:
        if scheme == "tcp":
            return DEFAULT_CLIENT_PORT_TCP

        if scheme == "grpc":
            return DEFAULT_CLIENT_PORT_GRPC

        if scheme == "http":
            return DEFAULT_CLIENT_PORT_HTTP

    if client_type == ClientType.WORKER:
        if scheme == "tcp":
            return DEFAULT_WORKER_PORT_TCP

        if scheme == "grpc":
            return DEFAULT_WORKER_PORT_GRPC

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
            return

        # IPv4 or hostname with optional port
        if ":" in self.raw_target:
            host_part, port_part = self.raw_target.rsplit(":", 1)
            self.host = host_part
            self.family = socket.AF_INET
            try:
                self.port = int(port_part)
            except ValueError:
                raise ValueError(
                    f"Invalid port number in target: {self.raw_target}"
                )
        else:
            self.host = self.raw_target
            self.port = None


@dataclass
class TransportOptions:
    scheme: str
    target: str

    @classmethod
    def from_args(cls, url: str) -> "TransportOptions":
        """
        Create a TransportOptions instance from command line arguments.
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
            raise ValueError(f"Invalid URL format: {url}")

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

    parsed = TransportOptions.from_args(addr)
    default_port = get_port(parsed.scheme, client_type)

    if parsed.scheme == "tcp":
        ct = ConnectionTarget(parsed.target)
        return TcpClient(
            host=ct.host,
            port=ct.port or default_port,
            ssl=ssl_context,
            family=socket.AF_INET6 if ct.is_ipv6 else socket.AF_INET,
        )

    elif parsed.scheme == "socket":
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

        return HttpClient(
            target=new_target,
            ssl_context=ssl_context,
        )

    raise ValueError(f"Unknown scheme: {parsed.scheme}")


def client_to_broker(
    addr: str,
    ssl_client_options: typing.Optional[SSLClientOptions] = None,
    ssl_context: typing.Optional[ssl.SSLContext] = None,
) -> ClientTransport:
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

    parsed = TransportOptions.from_args(addr)
    default_port = get_port(parsed.scheme, client_type)

    if parsed.scheme == "tcp":
        ct = ConnectionTarget(parsed.target)

        return TcpServer(
            hosts=ct.host,
            port=ct.port or default_port,
            ssl=ssl_context,
            family=socket.AF_INET6 if ct.is_ipv6 else socket.AF_INET,
        )

    elif parsed.scheme == "socket":
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

        return HttpServer(
            host=new_target,
            ssl_options=ssl_server_options,
        )

    raise ValueError(f"Unknown scheme: {parsed.scheme}")


def broker_for_workers(
    addresses: typing.List[str],
    ssl_server_options: typing.Optional[SSLServerOptions] = None,
    ssl_context: typing.Optional[ssl.SSLContext] = None,
) -> typing.List[ServerTransport]:
    rc = []
    for addr in addresses:
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
    rc = []
    for addr in addresses:
        rc.append(
            server_connection(
                addr,
                ClientType.CLIENT,
                ssl_server_options,
                ssl_context,
            )
        )
    return rc

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import argparse

from abc import ABC, abstractmethod

from .exit_code import ExitCode


class BaseCommand(ABC):

    @classmethod
    @abstractmethod
    def command(cls) -> str: ...

    @classmethod
    @abstractmethod
    def help(cls) -> str: ...

    @classmethod
    @abstractmethod
    def description(cls) -> str: ...

    @classmethod
    @abstractmethod
    def build_parser(cls, parser: argparse.ArgumentParser): ...

    @classmethod
    def add_default_options(
        cls,
        parser: argparse.ArgumentParser,
    ):
        group = parser.add_argument_group("Common Options")
        group.add_argument(
            "--log-level",
            dest="log_levels",
            action="append",
            default=[],
            metavar="<LEVEL or LOGGER=LEVEL>",
            help="Set the logging level globally or for a specific logger. (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        )

    @classmethod
    def add_db_options(
        cls,
        parser: argparse.ArgumentParser,
    ):
        group = parser.add_argument_group("Database Options")
        group.add_argument(
            "--db-url",
            dest="db_url",
            action="store",
            metavar="<URL>",
            help="URL to database. Two example: 'postgresql+asyncpg://user@/db' or 'sqlite+aiosqlite://./db.sqlite'",
        )
        group.add_argument(
            "--db-pool-size",
            dest="db_pool_size",
            action="store",
            default=10,
            type=int,
            metavar="<number>",
            help="Size of the database connection pool. Default is 10.",
        )
        group.add_argument(
            "--db-max-overflow",
            dest="db_max_overflow",
            action="store",
            default=20,
            type=int,
            metavar="<number>",
            help="Maximum overflow size of the database connection pool. Default is 20.",
        )
        group.add_argument(
            "--db-pool-recycle",
            dest="db_pool_recycle",
            action="store",
            default=300,
            type=int,
            metavar="<number>",
            help="Time in seconds to recycle connections in the pool. Default is 300.",
        )
        group.add_argument(
            "--db-pool-timeout",
            dest="db_pool_timeout",
            action="store",
            default=30,
            type=int,
            metavar="<number>",
            help="Timeout in seconds for acquiring a connection from the pool. Default is 30.",
        )

    @classmethod
    def add_ssl_client_options(
        cls,
        parser: argparse.ArgumentParser,
    ):
        group = parser.add_argument_group("SSL/TLS Client Options")

        group.add_argument(
            "--ssl",
            action="store_true",
            default=False,
            help="Enable SSL/TLS",
        )
        group.add_argument(
            "--cert",
            metavar="<path>",
            default=None,
            help="Path to client certificate (PEM format)",
        )
        group.add_argument(
            "--key",
            metavar="<path>",
            default=None,
            help="Path to client private key (PEM format)",
        )
        group.add_argument(
            "--ca",
            metavar="<path>",
            default=None,
            help="Path to CA bundle or root certificate (for verifying server)",
        )
        group.add_argument(
            "--no-verify",
            default=False,
            help="Disable certificate verification (insecure, for testing)",
        )
        group.add_argument(
            "--ciphers",
            default=None,
            metavar="<cipher_list>",
            help="Custom list of ciphers (OpenSSL syntax)",
        )
        group.add_argument(
            "--tls-version",
            default=None,
            metavar="<version>",
            help="TLS version to use: 1.2, 1.3, etc.",
        )
        group.add_argument(
            "--verify-hostname",
            action="store_true",
            default=False,
            help="Enforce hostname verification",
        )

    @classmethod
    def add_ssl_server_options(
        cls,
        parser: argparse.ArgumentParser,
    ):
        group = parser.add_argument_group("SSL/TLS Server Options")

        group.add_argument(
            "--ssl",
            action="store_true",
            default=False,
            help="Enable SSL/TLS",
        )
        group.add_argument(
            "--cert",
            metavar="<path>",
            default=None,
            help="Path to server certificate (PEM format)",
        )
        group.add_argument(
            "--key",
            metavar="<path>",
            default=None,
            help="Path to server private key (PEM format)",
        )
        group.add_argument(
            "--ca",
            metavar="<path>",
            default=None,
            help="Path to CA bundle to verify client certs (for mTLS)",
        )
        group.add_argument(
            "--require-client-cert",
            default=False,
            help="Enfore mutual TLS (client must provide valid cert)",
        )
        group.add_argument(
            "--ciphers",
            default=None,
            metavar="<cipher_list>",
            help="Custom list of ciphers (OpenSSL syntax)",
        )
        group.add_argument(
            "--tls-version",
            default=None,
            metavar="<version>",
            help="TLS version to use: 1.2, 1.3, etc.",
        )


class Command(BaseCommand):

    @abstractmethod
    def main(self, args: argparse.Namespace, rem: typing.List[str]) -> ExitCode:
        """
        Main method.
        """
        pass


class AsyncCommand(BaseCommand):

    @abstractmethod
    async def main(
        self, args: argparse.Namespace, rem: typing.List[str]
    ) -> ExitCode:
        """
        Main method.
        """
        pass

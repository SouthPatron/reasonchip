# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import logging
import typing
import argparse

from abc import ABC, abstractmethod

from .exit_code import ExitCode

log = logging.getLogger(__name__)


class BaseCommand(ABC):

    @classmethod
    @abstractmethod
    def command(cls) -> str:
        """
        Return the command string associated with this command.

        :return: The command as a string.
        """
        ...

    @classmethod
    @abstractmethod
    def help(cls) -> str:
        """
        Return the help string for the command.

        :return: The help description.
        """
        ...

    @classmethod
    @abstractmethod
    def description(cls) -> str:
        """
        Return the full description for the command.

        :return: The command description.
        """
        ...

    @classmethod
    @abstractmethod
    def build_parser(cls, parser: argparse.ArgumentParser):
        """
        Build the argument parser for this command.

        :param parser: The argparse.ArgumentParser instance to configure.
        """
        ...

    @classmethod
    def add_default_options(
        cls,
        parser: argparse.ArgumentParser,
    ):
        """
        Add common options used by many commands to the parser.

        :param parser: The argparse.ArgumentParser instance to add options to.
        """
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
    def add_ssl_client_options(
        cls,
        parser: argparse.ArgumentParser,
    ):
        """
        Add SSL/TLS client-related options to the parser.

        :param parser: The argparse.ArgumentParser instance to add options to.
        """
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
        """
        Add SSL/TLS server-related options to the parser.

        :param parser: The argparse.ArgumentParser instance to add options to.
        """
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
        The main method to execute the command.

        :param args: Parsed command line arguments namespace.
        :param rem: Remaining command line arguments that were not parsed.

        :return: ExitCode representing success or failure.
        """
        pass


class AsyncCommand(BaseCommand):

    @abstractmethod
    async def main(
        self, args: argparse.Namespace, rem: typing.List[str]
    ) -> ExitCode:
        """
        The async main method to execute the command.

        :param args: Parsed command line arguments namespace.
        :param rem: Remaining command line arguments that were not parsed.

        :return: ExitCode representing success or failure.
        """
        pass

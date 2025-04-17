# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import argparse
import typing
import ssl
import logging

from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class SSLClientOptions:
    cert: typing.Optional[str] = field(default=None)
    key: typing.Optional[str] = field(default=None)
    ca: typing.Optional[str] = field(default=None)
    no_verify: bool = field(default=False)
    ciphers: typing.Optional[str] = field(default=None)
    tls_version: typing.Optional[str] = field(default=None)
    verify_hostname: bool = field(default=False)

    @classmethod
    def from_args(
        cls, args: argparse.Namespace
    ) -> typing.Optional["SSLClientOptions"]:
        """
        Create an SSLClientOptions instance from command line arguments.

        :param args: argparse.Namespace containing the CLI arguments
        :return: SSLClientOptions instance if ssl is enabled in args else None
        """

        if not getattr(args, "ssl", False):
            log.debug("SSL is not enabled in the arguments; returning None.")
            return None

        options = cls(
            cert=getattr(args, "cert", None),
            key=getattr(args, "key", None),
            ca=getattr(args, "ca", None),
            no_verify=getattr(args, "no_verify", False),
            ciphers=getattr(args, "ciphers", None),
            tls_version=getattr(args, "tls_version", None),
            verify_hostname=getattr(args, "verify_hostname", False),
        )
        log.debug(f"Created SSLClientOptions from args: {options}")
        return options

    def create_ssl_context(self) -> ssl.SSLContext:
        """
        Create and configure an SSLContext for the client based on the options.

        :return: Configured ssl.SSLContext instance
        """
        log.info("Creating SSL context for client.")
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

        if self.no_verify:
            log.debug(
                "Disabling certificate verification and hostname checking."
            )
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            log.debug(
                f"Setting verify_hostname to {self.verify_hostname} and verify_mode to CERT_REQUIRED."
            )
            context.check_hostname = self.verify_hostname
            context.verify_mode = ssl.CERT_REQUIRED

        if self.ca:
            log.debug(f"Loading CA certificates from {self.ca}.")
            context.load_verify_locations(cafile=self.ca)

        if self.cert and self.key:
            log.debug(f"Loading client cert {self.cert} and key {self.key}.")
            context.load_cert_chain(certfile=self.cert, keyfile=self.key)

        if self.ciphers:
            log.debug(f"Setting ciphers to {self.ciphers}.")
            context.set_ciphers(self.ciphers)

        if self.tls_version:
            log.debug(f"Enforcing TLS version {self.tls_version}.")
            self._enforce_tls_version(context)

        log.info("SSL client context created successfully.")
        return context

    def _enforce_tls_version(self, context: ssl.SSLContext):
        """
        Enforce a specific TLS version on the SSLContext.

        :param context: ssl.SSLContext to configure
        """
        log.debug(
            f"Configuring TLS version enforcement for version: {self.tls_version}."
        )
        if self.tls_version == "1.2":
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_2
        elif self.tls_version == "1.3":
            context.minimum_version = ssl.TLSVersion.TLSv1_3
            context.maximum_version = ssl.TLSVersion.TLSv1_3
        else:
            log.error(f"Unsupported TLS version specified: {self.tls_version}")
            raise ValueError(f"Unsupported TLS version: {self.tls_version}")


@dataclass
class SSLServerOptions:
    cert: typing.Optional[str] = field(default=None)
    key: typing.Optional[str] = field(default=None)
    ca: typing.Optional[str] = field(default=None)
    require_client_cert: bool = field(default=False)
    ciphers: typing.Optional[str] = field(default=None)
    tls_version: typing.Optional[str] = field(default=None)

    @classmethod
    def from_args(
        cls, args: argparse.Namespace
    ) -> typing.Optional["SSLServerOptions"]:
        """
        Create an SSLServerOptions instance from command line arguments.

        :param args: argparse.Namespace containing CLI arguments
        :return: SSLServerOptions instance if ssl is enabled else None
        """

        if not getattr(args, "ssl", False):
            log.debug("SSL is not enabled in the arguments; returning None.")
            return None

        options = cls(
            cert=getattr(args, "cert", None),
            key=getattr(args, "key", None),
            ca=getattr(args, "ca", None),
            require_client_cert=getattr(args, "require_client_cert", False),
            ciphers=getattr(args, "ciphers", None),
            tls_version=getattr(args, "tls_version", None),
        )
        log.debug(f"Created SSLServerOptions from args: {options}")
        return options

    def create_ssl_context(self) -> ssl.SSLContext:
        """
        Create and configure an SSLContext for the server based on the options.

        :return: Configured ssl.SSLContext instance
        :raises ValueError: If cert or key is not provided
        """
        log.info("Creating SSL context for server.")
        if not self.cert or not self.key:
            log.error("Server cert and key must be provided for SSL.")
            raise ValueError("Server cert and key must be provided for SSL.")

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=self.cert, keyfile=self.key)

        if self.ca:
            log.debug(f"Loading CA certificates from {self.ca}.")
            context.load_verify_locations(cafile=self.ca)

        if self.require_client_cert:
            log.debug(
                "Setting verify_mode to CERT_REQUIRED due to require_client_cert=True."
            )
            context.verify_mode = ssl.CERT_REQUIRED
        else:
            log.debug(
                "Setting verify_mode to CERT_NONE as require_client_cert=False."
            )
            context.verify_mode = ssl.CERT_NONE

        if self.ciphers:
            log.debug(f"Setting ciphers to {self.ciphers}.")
            context.set_ciphers(self.ciphers)

        if self.tls_version:
            log.debug(f"Enforcing TLS version {self.tls_version}.")
            self._enforce_tls_version(context)

        log.info("SSL server context created successfully.")
        return context

    def _enforce_tls_version(self, context: ssl.SSLContext):
        """
        Enforce a specific TLS version on the SSLContext.

        :param context: ssl.SSLContext to configure
        """
        log.debug(
            f"Configuring TLS version enforcement for version: {self.tls_version}."
        )
        if self.tls_version == "1.2":
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_2
        elif self.tls_version == "1.3":
            context.minimum_version = ssl.TLSVersion.TLSv1_3
            context.maximum_version = ssl.TLSVersion.TLSv1_3
        else:
            log.error(f"Unsupported TLS version specified: {self.tls_version}")
            raise ValueError(f"Unsupported TLS version: {self.tls_version}")

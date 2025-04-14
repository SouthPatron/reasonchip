# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import argparse
import typing
import ssl

from dataclasses import dataclass, field


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

        if not getattr(args, "ssl", False):
            return None

        return cls(
            cert=getattr(args, "cert", None),
            key=getattr(args, "key", None),
            ca=getattr(args, "ca", None),
            no_verify=getattr(args, "no_verify", False),
            ciphers=getattr(args, "ciphers", None),
            tls_version=getattr(args, "tls_version", None),
            verify_hostname=getattr(args, "verify_hostname", False),
        )

    def create_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)

        if self.no_verify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            context.check_hostname = self.verify_hostname
            context.verify_mode = ssl.CERT_REQUIRED

        if self.ca:
            context.load_verify_locations(cafile=self.ca)

        if self.cert and self.key:
            context.load_cert_chain(certfile=self.cert, keyfile=self.key)

        if self.ciphers:
            context.set_ciphers(self.ciphers)

        if self.tls_version:
            self._enforce_tls_version(context)

        return context

    def _enforce_tls_version(self, context: ssl.SSLContext):
        if self.tls_version == "1.2":
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_2
        elif self.tls_version == "1.3":
            context.minimum_version = ssl.TLSVersion.TLSv1_3
            context.maximum_version = ssl.TLSVersion.TLSv1_3
        else:
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

        if not getattr(args, "ssl", False):
            return None

        return cls(
            cert=getattr(args, "cert", None),
            key=getattr(args, "key", None),
            ca=getattr(args, "ca", None),
            require_client_cert=getattr(args, "require_client_cert", False),
            ciphers=getattr(args, "ciphers", None),
            tls_version=getattr(args, "tls_version", None),
        )

    def create_ssl_context(self) -> ssl.SSLContext:
        if not self.cert or not self.key:
            raise ValueError("Server cert and key must be provided for SSL.")

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=self.cert, keyfile=self.key)

        if self.ca:
            context.load_verify_locations(cafile=self.ca)

        if self.require_client_cert:
            context.verify_mode = ssl.CERT_REQUIRED
        else:
            context.verify_mode = ssl.CERT_NONE

        if self.ciphers:
            context.set_ciphers(self.ciphers)

        if self.tls_version:
            self._enforce_tls_version(context)

        return context

    def _enforce_tls_version(self, context: ssl.SSLContext):
        if self.tls_version == "1.2":
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_2
        elif self.tls_version == "1.3":
            context.minimum_version = ssl.TLSVersion.TLSv1_3
            context.maximum_version = ssl.TLSVersion.TLSv1_3
        else:
            raise ValueError(f"Unsupported TLS version: {self.tls_version}")

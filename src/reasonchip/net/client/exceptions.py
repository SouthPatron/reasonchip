# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import typing
import uuid

from ..protocol import ResultCode

from ...core.exceptions import ReasonChipException


class ClientException(ReasonChipException):
    pass


class ConnectionException(ClientException):
    pass


class RemoteException(ClientException):
    """Base exception for all client-related errors."""

    def __init__(
        self,
        cookie: typing.Optional[uuid.UUID] = None,
        rc: typing.Optional[ResultCode] = None,
        error: typing.Optional[str] = None,
        stacktrace: typing.Optional[typing.List[str]] = None,
    ):
        super().__init__()
        self.cookie = cookie
        self.rc = rc
        self.error = error
        self.stacktrace = stacktrace


class BadPacketException(RemoteException):
    pass


class UnsupportedPacketTypeException(RemoteException):
    pass


class NoCapacityException(RemoteException):
    pass


class CookieNotFoundException(RemoteException):
    pass


class CookieCollisionException(RemoteException):
    pass


class BrokerWentAwayException(RemoteException):
    pass


class WorkerWentAwayException(RemoteException):
    pass


class ProcessorException(RemoteException):
    pass


class GeneralException(RemoteException):
    pass

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from ...core.exceptions import ReasonChipException


class ClientException(ReasonChipException):
    pass


class ConnectionException(ClientException):
    pass


class BadPacketException(ClientException):
    pass


class UnsupportedPacketTypeException(ClientException):
    pass


class NoCapacityException(ClientException):
    pass


class CookieNotFoundException(ClientException):
    pass


class CookieCollisionException(ClientException):
    pass


class BrokerWentAwayException(ClientException):
    pass


class WorkerWentAwayException(ClientException):
    pass


class RemoteException(ClientException):
    pass

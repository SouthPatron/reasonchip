# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing
import logging

log = logging.getLogger(__name__)


class Facilities:
    """
    Singleton class representing facilities.

    This class ensures only one instance is created.
    """

    _instance: typing.Optional[Facilities] = None

    def __new__(cls):
        """
        Create a new instance if one does not exist, else return the existing instance.

        :return: The singleton instance of Facilities
        """
        if cls._instance is None:
            log.info("Creating new instance of Facilities singleton")
            cls._instance = super().__new__(cls)
        else:
            log.info("Returning existing instance of Facilities singleton")
        return cls._instance

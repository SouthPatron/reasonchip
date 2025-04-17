# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing
import json
import datetime
import logging

from dotty_dict import dotty, Dotty

log = logging.getLogger(__name__)


class Config:
    def __init__(self, kvp: typing.Dict[str, str] = {}) -> None:
        """
        Initialize a Config object with an optional dictionary of key-value pairs.

        :param kvp: Optional initial dictionary of string keys and string values.
        """
        self._kvp: Dotty = dotty(kvp)
        log.debug(f"Config initialized with keys: {list(kvp.keys())}")

    @property
    def kvp(self) -> Dotty:
        """
        Return the internal Dotty dictionary representing configuration.

        :return: Dotty object wrapping the key-value pairs.
        """
        return self._kvp

    def has(self, key: str) -> bool:
        """
        Check if the configuration has a particular key.

        :param key: The key to check in the configuration.

        :return: True if the key exists, False otherwise.
        """
        result = key in self._kvp
        log.debug(f"Checking presence of key '{key}': {result}")
        return result

    def setDefaults(self, kvp: typing.Dict[str, str]) -> Config:
        """
        Update the configuration with default key-value pairs.
        Existing keys will be updated.

        :param kvp: Dictionary of default key-value pairs to set.

        :return: The updated Config instance.
        """
        self._kvp.update(kvp)
        log.info(f"Defaults set/updated with keys: {list(kvp.keys())}")
        return self

    def setValue(self, key: str, value: str) -> Config:
        """
        Set a specific key to a given string value in the configuration.

        :param key: The key to set.
        :param value: The string value to assign to the key.

        :return: The updated Config instance.
        """
        self._kvp[key] = value
        log.info(f"Set value for key '{key}'")
        return self

    def getBool(self, key: str) -> bool:
        """
        Retrieve the boolean interpretation of the string value associated with a key.
        Matches against a list of strings representing True values.

        :param key: The key whose value to interpret as boolean.

        :return: Boolean interpretation of the value.
        """
        val = self.getStr(key).lower()
        true_values = [
            "true",
            "yes",
            "1",
            "on",
            "enabled",
            "ja",
            "yebo",
            "yup",
            "yep",
            "y",
        ]
        result = val in true_values
        log.debug(
            f"Boolean lookup for key '{key}' with value '{val}': {result}"
        )
        return result

    def getFloat(self, key: str) -> float:
        """
        Retrieve the float representation of the value associated with a key.

        :param key: The key whose value to convert to float.

        :return: Floating point number representing the value.
        """
        val = float(self.getStr(key))
        log.debug(f"Float lookup for key '{key}' with value '{val}'")
        return val

    def getInt(self, key: str) -> int:
        """
        Retrieve the integer representation of the value associated with a key.

        :param key: The key whose value to convert to integer.

        :return: Integer representing the value.
        """
        val = int(self.getStr(key))
        log.debug(f"Integer lookup for key '{key}' with value '{val}'")
        return val

    def getStr(self, key: str) -> str:
        """
        Retrieve the string value associated with a key.

        :param key: The key whose value to return.

        :return: String value corresponding to the key.
        """
        val = str(self._kvp[key])
        log.debug(f"String lookup for key '{key}' with value '{val}'")
        return val

    def getJson(self, key: str) -> typing.Any:
        """
        Retrieve the value associated with a key and parse it as JSON.

        :param key: The key whose value to parse as JSON.

        :return: Parsed JSON object.
        """
        val = json.loads(self.getStr(key))
        log.debug(f"JSON lookup for key '{key}' with parsed value: {val}")
        return val

    def getDate(self, key: str) -> datetime.date:
        """
        Retrieve the date value associated with a key.
        The string is expected to be in 'YYYY-MM-DD' format.

        :param key: The key whose value to parse as date.

        :return: datetime.date object representing the date.
        """
        val_str = self.getStr(key)
        val_date = datetime.datetime.strptime(val_str, "%Y-%m-%d").date()
        log.debug(
            f"Date lookup for key '{key}' with value '{val_str}' parsed as {val_date}"
        )
        return val_date

    def getNamespace(self, namespace: str) -> Config:
        """
        Retrieve a subsection of the configuration as a new Config object.

        :param namespace: The namespace key to retrieve.

        :return: A new Config configured with values under the specified namespace.
        """
        ns = self._kvp[namespace]
        rc = dict(ns)
        log.debug(
            f"Namespace '{namespace}' extracted with keys: {list(rc.keys())}"
        )
        return Config(rc)

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing
import json
import datetime

from dotty_dict import dotty, Dotty


class Config:
    def __init__(self, kvp: typing.Dict[str, str] = {}) -> None:
        self._kvp: Dotty = dotty(kvp)

    @property
    def kvp(self) -> Dotty:
        return self._kvp

    def has(self, key: str) -> bool:
        return key in self._kvp

    def setDefaults(self, kvp: typing.Dict[str, str]) -> Config:
        self._kvp.update(kvp)
        return self

    def setValue(self, key: str, value: str) -> Config:
        self._kvp[key] = value
        return self

    def getBool(self, key: str) -> bool:
        return self.getStr(key).lower() in [
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

    def getFloat(self, key: str) -> float:
        return float(self.getStr(key))

    def getInt(self, key: str) -> int:
        return int(self.getStr(key))

    def getStr(self, key: str) -> str:
        return str(self._kvp[key])

    def getJson(self, key: str) -> typing.Any:
        return json.loads(self.getStr(key))

    def getDate(self, key: str) -> datetime.date:
        return datetime.datetime.strptime(self.getStr(key), "%Y-%m-%d").date()

    def getNamespace(self, namespace: str) -> Config:
        ns = self._kvp[namespace]
        rc = dict(ns)
        return Config(rc)

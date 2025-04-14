# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import os
import typing

from configparser import ConfigParser, BasicInterpolation

from ..exceptions import ConfigurationException

from .config import Config


class EnvInterpolation(BasicInterpolation):
    """Interpolation which expands environment variables in values."""

    def before_get(self, parser, section, option, value, defaults):
        value = super().before_get(parser, section, option, value, defaults)
        return os.path.expandvars(value)


class Loader:

    _reserved_words: typing.List[str] = [
        "logging",
        "defaults",
    ]

    def __init__(self, filename: str) -> None:
        self._filename: str = filename

    @property
    def services(self) -> typing.List[str]:
        cfg = self._load(self._filename, "bob")
        total = cfg.sections()
        rc = [i for i in total if i not in self._reserved_words]
        return rc

    def service(self, service_name: str) -> Config:
        cfg = self._load(self._filename, service_name)
        rc: typing.Dict = {}
        rc.update(self._getsection(cfg, "defaults", False))
        rc.update(self._getsection(cfg, service_name, False))
        rc.pop("cwd")
        return Config(rc)

    def logging(self, service_name: str) -> str:
        cfg = self._load(self._filename, service_name)
        return self._getoption(cfg, "logging", "config")

    def _load(
        self,
        filename: str,
        service_name: str,
    ) -> ConfigParser:
        if service_name in self._reserved_words:
            raise ConfigurationException(
                f"Service name [{service_name}] is a reserved word."
            )

        configpath = os.path.dirname(filename)
        sysconfig = ConfigParser(
            defaults={
                "cwd": configpath,
            },
            interpolation=EnvInterpolation(),
        )
        num = sysconfig.read(filename)
        if len(num) != 1:
            raise ConfigurationException(
                f"Unable to read configuration file: [{filename}]"
            )

        return sysconfig

    def _getoption(
        self,
        cfg: ConfigParser,
        section: str,
        option: str,
    ) -> str:
        if not cfg.has_option(section, option):
            raise ConfigurationException(
                f"Missing option: [{section}] {option}"
            )
        return cfg[section][option]

    def _getsection(
        self,
        cfg: ConfigParser,
        section: str,
        required: bool = True,
    ) -> typing.Dict:
        if not cfg.has_section(section):
            if required:
                raise ConfigurationException(f"Missing section: [{section}]")
            return dict()
        return dict(cfg[section])

    def _find_config_file(
        self,
        filename: str,
        appname: str,
    ) -> typing.Optional[str]:

        home: str = os.path.expanduser("~")

        search_paths = [
            os.path.join(home, f".{appname}", filename),
            os.path.join(home, ".config", appname, filename),
            os.path.join("/etc", appname, filename),
        ]
        for path in search_paths:
            if os.path.exists(path):
                return path

        return None

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import os
import typing
import logging

from configparser import ConfigParser, BasicInterpolation

from ..exceptions import ConfigurationException

from .config import Config

log = logging.getLogger(__name__)


class EnvInterpolation(BasicInterpolation):
    """Interpolation which expands environment variables in values."""

    def before_get(self, parser, section, option, value, defaults):
        value = super().before_get(parser, section, option, value, defaults)
        log.debug(
            f"Expanding environment variables in {section}:{option} with value: {value}"
        )
        return os.path.expandvars(value)


class Loader:

    _reserved_words: typing.List[str] = [
        "logging",
        "defaults",
    ]

    def __init__(self, filename: str) -> None:
        """
        Initialize the Loader with the configuration filename.

        :param filename: The path to the configuration file.
        """
        self._filename: str = filename
        log.info(f"Loader initialized with config file: {filename}")

    @property
    def services(self) -> typing.List[str]:
        """
        Retrieve the list of configured services excluding reserved words.

        :return: List of service section names.
        """
        cfg = self._load(self._filename, "bob")
        total = cfg.sections()
        rc = [i for i in total if i not in self._reserved_words]
        log.debug(f"Available services: {rc}")
        return rc

    def service(self, service_name: str) -> Config:
        """
        Retrieve the configuration for a given service, merged with defaults.

        :param service_name: The name of the service.

        :return: Config object with merged settings.
        """
        cfg = self._load(self._filename, service_name)
        rc: typing.Dict = {}

        # Merge defaults and service section
        rc.update(self._getsection(cfg, "defaults", False))
        rc.update(self._getsection(cfg, service_name, False))

        if "cwd" in rc:
            rc.pop("cwd")

        log.debug(f"Configuration loaded for service {service_name}: {rc}")
        return Config(rc)

    def logging(self, service_name: str) -> str:
        """
        Retrieve the logging configuration file path from the config.

        :param service_name: The name of the service.

        :return: Path to logging configuration.
        """
        cfg = self._load(self._filename, service_name)
        log_config = self._getoption(cfg, "logging", "config")
        log.debug(f"Logging config for {service_name}: {log_config}")
        return log_config

    def _load(
        self,
        filename: str,
        service_name: str,
    ) -> ConfigParser:
        """
        Load the configuration file and ensure the service name is not reserved.

        :param filename: The configuration filename.
        :param service_name: The service name to validate.

        :return: ConfigParser instance with the configuration loaded.
        """
        if service_name in self._reserved_words:
            log.error(
                f"Attempted to load reserved service name: {service_name}"
            )
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
            log.error(f"Failed to read configuration file: {filename}")
            raise ConfigurationException(
                f"Unable to read configuration file: [{filename}]"
            )
        log.debug(f"Configuration file {filename} loaded successfully")
        return sysconfig

    def _getoption(
        self,
        cfg: ConfigParser,
        section: str,
        option: str,
    ) -> str:
        """
        Retrieve an option's value from a configuration section.

        :param cfg: The ConfigParser instance.
        :param section: Section name in the configuration.
        :param option: Option name within the section.

        :return: The value of the option.
        """
        if not cfg.has_option(section, option):
            log.error(f"Missing option '{option}' in section '{section}'")
            raise ConfigurationException(
                f"Missing option: [{section}] {option}"
            )
        value = cfg[section][option]
        log.debug(f"Option retrieved - [{section}] {option}: {value}")
        return value

    def _getsection(
        self,
        cfg: ConfigParser,
        section: str,
        required: bool = True,
    ) -> typing.Dict:
        """
        Retrieve all options in a configuration section as a dictionary.

        :param cfg: The ConfigParser instance.
        :param section: Section name to retrieve.
        :param required: If True, raise exception if section missing.

        :return: Dictionary of options in the section.
        """
        if not cfg.has_section(section):
            if required:
                log.error(f"Missing required section: {section}")
                raise ConfigurationException(f"Missing section: [{section}]")
            log.debug(
                f"Optional section [{section}] not found, returning empty dict"
            )
            return dict()
        section_dict = dict(cfg[section])
        log.debug(f"Section [{section}] loaded with options: {section_dict}")
        return section_dict

    def _find_config_file(
        self,
        filename: str,
        appname: str,
    ) -> typing.Optional[str]:
        """
        Find a configuration file in standard locations.

        :param filename: Name of the configuration file.
        :param appname: Application name used in path.

        :return: Full path to config file if found, else None.
        """
        home: str = os.path.expanduser("~")

        search_paths = [
            os.path.join(home, f".{appname}", filename),
            os.path.join(home, ".config", appname, filename),
            os.path.join("/etc", appname, filename),
        ]

        # Check each path for existence of the file
        for path in search_paths:
            if os.path.exists(path):
                log.debug(f"Config file found at: {path}")
                return path

        log.debug(
            f"Config file {filename} not found in standard locations for {appname}"
        )
        return None

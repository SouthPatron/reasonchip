# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

import logging
import logging.config
import typing
import re
import os

from importlib.resources import files

log = logging.getLogger(__name__)


def configure_logging(
    log_levels: typing.Optional[typing.List[str]] = None,
):
    """
    Configures the logging settings for the application.

    :param log_levels: Optional list of log level strings in the format LOGGER=LEVEL or LEVEL.
    """

    # Load the default logging configuration file from common paths
    logcfgs = [
        "~/.reasonchip/logging.conf",
        "/etc/reasonchip/logging.conf",
        str(files("reasonchip.data") / ("logging.conf")),
    ]

    # Check each possible config location and load the first config file found
    for cfg in logcfgs:
        fname = os.path.expanduser(cfg)
        if os.path.exists(fname):
            logging.config.fileConfig(fname)
            log.info(f"Loaded logging configuration from {fname}")
            break

    # Extract all the log levels requested
    lv = log_levels or []

    # Default levels for the root logger
    default_level = logging.getLogger().level

    levels = {"root": default_level}

    # Parse each log level string and populate levels dictionary
    for level in lv:
        if match := re.match(
            r"^([A-Za-z0-9.\-]+)=(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
            level,
            flags=re.IGNORECASE,
        ):
            logger_name = match.group(1)
            logger_level = match.group(2).upper()

            levels[logger_name] = getattr(logging, logger_level)
            log.info(f"Set log level for {logger_name} to {logger_level}")

        elif match := re.match(
            r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
            level,
            flags=re.IGNORECASE,
        ):
            logger_level = match.group(1).upper()
            levels["root"] = getattr(logging, logger_level)
            log.info(f"Set root log level to {logger_level}")

        else:
            raise ValueError(
                f"Invalid log level format: {level}. Expected format: LOGGER=LEVEL or LEVEL. Options are [DEBUG, INFO, WARNING, ERROR, CRITICAL]"
            )

    # Get the syslog handler from the logging config
    syslog_handler = logging.getHandlerByName("syslog")
    assert syslog_handler, "syslog handler not found in logging configuration"

    # Set the root logger level
    logging.getLogger().setLevel(levels["root"])
    log.info(f"Root logger level set to {levels['root']}")

    # Update all existing loggers
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)

        if name in levels:
            level = levels[name]
            # Set level, disable propagation, reset handlers, then add syslog handler
            logger.setLevel(level)
            logger.propagate = False
            for h in logger.handlers:
                logger.removeHandler(h)
            logger.addHandler(syslog_handler)
            log.info(
                f"Updated logger {name} with level {level} and syslog handler"
            )

    # Hooking into logging.getLogger to patch loggers on first get
    original_get_logger = logging.getLogger

    def crafty_get_logger(name=None):
        """
        Get a patched logger that applies custom level and handler settings on first retrieval.

        :param name: The name of the logger.
        :return: The configured logger instance.
        """
        logger = original_get_logger(name)

        # Patch logger on first get if name is in levels
        if name and name in levels and not getattr(logger, "_crafty", False):
            logger.setLevel(levels[name])
            logger.propagate = False
            for h in logger.handlers:
                logger.removeHandler(h)
            logger.addHandler(syslog_handler)
            setattr(logger, "_crafty", True)
            log.info(
                f"Crafty logger setup for {name} with level {levels[name]}"
            )

        return logger

    logging.getLogger = crafty_get_logger

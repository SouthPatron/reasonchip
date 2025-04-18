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


def configure_logging(
    log_levels: typing.Optional[typing.List[str]] = None,
):
    """
    Configures the logging settings for the application.
    """

    # Load the default logging configuration file
    logcfgs = [
        "~/.reasonchip/logging.conf",
        "/etc/reasonchip/logging.conf",
        str(files("reasonchip.data") / ("logging.conf")),
    ]
    for cfg in logcfgs:
        fname = os.path.expanduser(cfg)
        if os.path.exists(fname):
            logging.config.fileConfig(fname)
            break

    # Extract all the log levels requested
    lv = log_levels or []

    # Default levels
    default_level = logging.getLogger().level

    levels = {"root": default_level}

    for level in lv:
        if match := re.match(
            r"^([A-Za-z0-9.\-]+)=(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
            level,
            flags=re.IGNORECASE,
        ):
            logger_name = match.group(1)
            logger_level = match.group(2).upper()

            levels[logger_name] = getattr(logging, logger_level)

        elif match := re.match(
            r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
            level,
            flags=re.IGNORECASE,
        ):
            logger_level = match.group(1).upper()
            levels["root"] = getattr(logging, logger_level)

        else:
            raise ValueError(
                f"Invalid log level format: {level}. Expected format: LOGGER=LEVEL or LEVEL. Options are [DEBUG, INFO, WARNING, ERROR, CRITICAL]"
            )

    # Get the handler
    syslog_handler = logging.getHandlerByName("syslog")
    assert syslog_handler, "syslog handler not found in logging configuration"

    # Set the root logger level
    logging.getLogger().setLevel(levels["root"])

    # Update all existing loggers
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)

        if name in levels:
            level = levels[name]
            logger.setLevel(level)
            logger.propagate = False
            for h in logger.handlers:
                logger.removeHandler(h)
            logger.addHandler(syslog_handler)

    # Hooking into the call
    original_get_logger = logging.getLogger

    def crafty_get_logger(name=None):
        logger = original_get_logger(name)

        if name and name in levels and not getattr(logger, "_crafty", False):
            logger.setLevel(levels[name])
            logger.propagate = False
            for h in logger.handlers:
                logger.removeHandler(h)
            logger.addHandler(syslog_handler)
            setattr(logger, "_crafty", True)

        return logger

    logging.getLogger = crafty_get_logger

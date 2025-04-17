# Logging

## Overview

This directory provides logging utilities and configuration support
for the ReasonChip project. It includes a custom log formatter
for enhanced exception logging and a configuration helper to set up
application logging from configuration files and runtime parameters.

## Filesystem Overview

| Location                    | Description                               |
|-----------------------------|-------------------------------------------|
| [system_formatter.py](./system_formatter.py) | Defines a custom log formatter with detailed exception output |
| [configure.py](./configure.py)               | Functions to initialize and configure logging from config files and log levels |

## SystemFormatter

`SystemFormatter` extends Python's `logging.Formatter` with the following:

- Formats timestamps in a consistent UTC format with millisecond precision.
- Enhances exception logging by appending the exception class, message,
  source filename, line number, and a single-line JSON-encoded stack trace
  to log messages.
- Overrides default exception formatting to avoid duplicated output.

This formatter is intended to provide concise but comprehensive messages
especially useful for system-level logs that require exception details.

## configure_logging

The `configure_logging` function initializes logging for the application:

- Attempts to load logging configuration from multiple sources, including
  user home, system path, and package resources.
- Parses optional log level overrides specified as strings in the format
  `LOGGER=LEVEL` or simply `LEVEL` for the root logger.
- Validates and applies these log levels to existing and future loggers.
- Ensures that all configured loggers use the same `syslog` handler from
  the loaded configuration, disables propagation to avoid duplicate logs,
  and resets handlers accordingly.
- Hooks into `logging.getLogger` to lazily apply level and handler changes
  on newly requested loggers matching the specified levels.

This approach centralizes logging setup and dynamically controls log verbosity
per logger while preserving handler consistency.

## Integration

Include `SystemFormatter` in logging configurations where detailed exception
information is desired. Use `configure_logging` early in application startup,
passing any runtime log level overrides as needed to configure log levels
and handlers appropriately.

## Notes

- The `syslog` handler must be defined in the logging configuration file for
  `configure_logging` to function correctly.
- Log levels must be specified as one of: DEBUG, INFO, WARNING, ERROR,
  or CRITICAL, case-insensitive.
- The custom formatter outputs times in UTC using the ISO-like format
  `YYYYMMDDTHHMMSSZ` with millisecond precision.

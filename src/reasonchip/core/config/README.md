# Configuration

## Overview

This directory provides configuration management support for the
application. It includes classes for loading configuration files,
parsing and merging service-specific and default configuration entries,
and providing a typed access interface to configuration values.

## Filesystem Overview

| Location         | Description                                  |
| ---------------- | --------------------------------------------|
| [config.py](./config.py)   | Core Config class wrapping key-value storage with typed accessors |
| [loader.py](./loader.py)   | Loader class to read and manage service configs and defaults, with environment variable support |

## Design and Usage

- **Config class**: Stores configuration key-value pairs in a
  dotty dictionary allowing nested access. Provides typed getters
  for bool, int, float, string, JSON, and date values, plus namespace
  subconfig extraction. Supports setting defaults and individual keys.

- **Loader class**: Reads `.ini` style configuration files,
  expanding environment variables in values. It enforces reserved
  section names and supports merging a `[defaults]` section with
  individual service sections. Also provides access to logging
  configuration file paths.

- **Environment variable interpolation** is integrated to allow
  dynamic values in config files.

- Configuration files are searched for in standard user and system
  locations.

## Exceptions

- Uses `ConfigurationException` (imported) to signal missing sections or options.

## Logging

- Uses the standard Python `logging` module to log configuration
  processing steps and errors.

This module is designed for robust and flexible configuration
management in complex applications with multiple services and
configurable environments.
# Configuration

## Overview

This directory contains classes and utilities for configuration
management within the ReasonChip project. It provides a structured way
to load, parse, and access configuration data, especially from INI
files, with support for environment variable expansion and type-safe
accessors.

## Filesystem Overview

| Location               | Description                             |
|------------------------|-------------------------------------|
| [config.py](./config.py)   | Core Config class for typed access and nested namespaces  |
| [loader.py](./loader.py)   | Loader for reading config files with environment variable interpolation |

## Onboarding Approach

Start with `Loader` in `loader.py` to understand how configuration
files are read and parsed. It uses `ConfigParser` with a custom
interpolation to expand environment variables. The loader supports
loading default sections and service-specific sections, merging them.

Next, examine `Config` in `config.py`. It provides a typed interface
for accessing configuration data stored as a nested dictionary
(Dotty). It supports conversion to boolean, integer, float, string,
JSON, and date types, and allows retrieval of sub-namespaces as
nested Config instances.

Understanding Python's `configparser` module, especially interpolation,
and the Dotty dictionary wrapper is essential. Also, familiarity with
INI file structure and environment variable patterns is helpful.

## Details

- `Config` encapsulates a dictionary with dot notation support via
  Dotty, allowing nested configuration keys like `database.host`.

- `Loader` reads an INI file, applies environment variable expansion
  for values, and exposes service names (sections excluding reserved
  ones) and configuration values.

- Reserved section names are `logging` and `defaults`; defaults are
  merged into service configs.

- `Loader` raises custom `ConfigurationException` errors when files,
  sections, or options are missing.

- The configuration current working directory (`cwd`) is set
  automatically to the directory of the config file but is removed
  from the returned config dictionary before passing to `Config`.

- `Loader` provides a method to find configuration file paths in
  user and system config directories but this method is currently
  unused.

This module forms the foundational layer for configuration handling
and should be used as a stable API for reading service-specific
settings across ReasonChip components.

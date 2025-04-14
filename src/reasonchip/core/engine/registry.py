# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing
import inspect
import os
import importlib
import importlib.util

from pydantic import BaseModel

from .. import exceptions as rex


# Define generics for request and response
RequestType = typing.TypeVar("RequestType", bound=BaseModel)
ResponseType = typing.TypeVar("ResponseType", bound=BaseModel)

# Define the chip type
ChipType = typing.Callable[
    [RequestType], typing.Coroutine[None, None, ResponseType]
]


# Define the registry types
class RegistryEntry(BaseModel):
    func: ChipType
    request_type: typing.Type[BaseModel]
    response_type: typing.Type[BaseModel]


RegistryType = typing.Dict[str, RegistryEntry]


# ----- Registry -------------------------------------------------------------


class Registry:

    def __new__(cls, *args, **kwargs):
        raise RuntimeError("Cannot instantiate Registry.")

    _registry: RegistryType = {}
    _search_path: typing.List[str] = [
        "reasonchip.chipsets",  # This is the default search path
    ]

    @classmethod
    def register(cls, func: ChipType) -> ChipType:
        module_name = func.__module__
        function_name = func.__name__
        clname = f"{module_name}.{function_name}"

        try:
            req, resp = cls.get_types(func)

            # NOTE: Don't check for duplicates
            cls._registry[clname] = RegistryEntry(
                func=func, request_type=req, response_type=resp
            )
            return func
        except rex.MalformedChipException as ex:
            raise rex.RegistryException(
                module_name=module_name,
                function_name=function_name,
            ) from ex

    @classmethod
    def registry(cls) -> RegistryType:
        return cls._registry

    @classmethod
    def register_chipsets(cls, path: str):
        if path not in cls._search_path:
            cls._search_path.append(path)

    @classmethod
    def get_chip(cls, name: str) -> typing.Optional[RegistryEntry]:

        # First we try to find it directly, if already loaded.
        if entry := Registry._hunt_chip(name):
            return entry

        # We have a registry miss. We have to search modules.
        if entry := Registry._hunt_modules(name):
            return entry

        # We have a total miss.
        return None

    @classmethod
    def get_types(
        cls, func: ChipType
    ) -> typing.Tuple[typing.Type[BaseModel], typing.Type[BaseModel]]:
        """
        Retrieve the request and response types from a chip function.
        """
        signature = inspect.signature(func)
        type_hints = typing.get_type_hints(func)

        # Extract parameter and return type
        params = list(signature.parameters.values())

        if len(params) != 1:
            raise rex.MalformedChipException(
                reason="Chip functions must have exactly one parameter."
            )

        request_type = type_hints[params[0].name]  # Get the request type
        response_type = type_hints["return"]  # Get the response type

        # Ensure both are subclasses of BaseModel
        if not issubclass(request_type, BaseModel) or not issubclass(
            response_type, BaseModel
        ):
            raise rex.MalformedChipException(
                reason="Request and response must be subclasses of Pydantic BaseModel."
            )

        return request_type, response_type

    @classmethod
    def _hunt_chip(cls, name: str) -> typing.Optional[RegistryEntry]:
        # Check for it directly
        if name in cls._registry:
            return cls._registry[name]

        # Now hunt backwards for it
        for path in reversed(cls._search_path):
            adjusted_name = f"{path}.{name}"
            if adjusted_name in cls._registry:
                return cls._registry[adjusted_name]

        return None

    @classmethod
    def _hunt_modules(cls, name: str) -> typing.Optional[RegistryEntry]:

        # Identify the module name
        module_name, _ = name.rsplit(".", 1)
        if not module_name:
            return None

        # Check for it directly
        if RegistryLoader.load_module(module_name):
            if name in cls._registry:
                return cls._registry[name]

        # Now hunt backwards for it
        for path in reversed(cls._search_path):
            full_mod = f"{path}.{module_name}"
            if RegistryLoader.load_module(full_mod):
                adjusted_name = f"{path}.{name}"
                if adjusted_name in cls._registry:
                    return cls._registry[adjusted_name]

        return None


# ----- Registry Loader ------------------------------------------------------


class RegistryLoader:

    @classmethod
    def load_module(cls, module_name: str) -> bool:
        try:

            importlib.import_module(module_name)
            return True

        except ModuleNotFoundError:
            return False

    @classmethod
    def load_module_tree(cls, module_name: str) -> bool:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            return False

        assert module.__file__ is not None

        RegistryLoader.load_filepath(module.__file__, module_name)

        return True

    @classmethod
    def load_filepath(cls, path: str, module_base: str):
        # Add the module to the search path
        Registry.register_chipsets(module_base)

        # Now load everything in there
        current_dir = os.path.dirname(path)

        for root, dirs, files in os.walk(current_dir, topdown=True):

            dirs[:] = [d for d in dirs if not d.startswith("_")]

            for file in files:
                if not file.endswith(".py") or file.startswith("_"):
                    continue

                module_path = os.path.join(root, file)

                # Convert the file path to a module name
                module_name = os.path.relpath(module_path, current_dir).replace(
                    os.sep, "."
                )[:-3]

                adjusted_module_name = f"{module_base}.{module_name}"

                importlib.import_module(adjusted_module_name)

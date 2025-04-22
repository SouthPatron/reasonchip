#!/usr/bin/env python

# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 South Patron LLC
# This file is part of ReasonChip and licensed under the GPLv3+.
# See <https://www.gnu.org/licenses/> for details.

from __future__ import annotations

import typing
import re
import munch

from ruamel.yaml import YAML

try:
    from .parsers import evaluator
except ImportError:
    from parsers import evaluator


VariableMapType = typing.Dict[str, typing.Any]


class Variables:

    def __init__(self, vmap: VariableMapType = {}) -> None:
        vm = munch.munchify(vmap)
        assert isinstance(vm, munch.Munch)
        self._vmap: munch.Munch = vm

    @property
    def vmap(self) -> munch.Munch:
        return self._vmap

    def copy(self) -> Variables:
        v = Variables()
        v._vmap = self._vmap.copy()  # type: ignore
        return v

    def load_file(self, filename: str):
        """
        Load variables from a file.

        :param filename: The file's name.
        """
        yml = YAML()
        with open(filename, "r") as f:
            v = yml.load(f)
            if not v:
                return

            if not isinstance(v, dict):
                raise ValueError(
                    f"Variable file must be a dictionary: {filename}"
                )

            self.update(v)

    def has(self, key: str) -> bool:
        return self.get(key)[0]

    def get(self, key: str) -> typing.Tuple[bool, typing.Any]:
        try:
            rc = eval(key, {"__builtins__": None}, self._vmap)
            return (True, rc)
        except Exception as e:
            return (False, None)

    def set(self, key: str, value: typing.Any) -> Variables:
        path = self._parse_key(key)
        self._set_path(self._vmap, path, munch.munchify(value))
        return self

    def _parse_key(self, key: str) -> list:
        pattern = r"""
            (?:^|\.)([a-zA-Z_][a-zA-Z0-9_]*)       # dot notation: foo.bar
            | \[\s*(['"]?)([^\[\]'"]+)\2\s*\]      # brackets: ["key"], [0]
        """
        parts = []
        for match in re.finditer(pattern, key, re.VERBOSE):
            if match.group(1):  # dot notation
                parts.append(match.group(1))
            elif match.group(3):  # bracket access
                part = match.group(3)
                try:
                    part = int(part)  # try as integer index
                except ValueError:
                    pass
                parts.append(part)
        return parts

    def _set_path(self, root: typing.Any, path: list, value: typing.Any):
        current = root
        for i, part in enumerate(path):
            is_last = i == len(path) - 1

            if is_last:
                current[part] = value
                return

            if isinstance(part, int):
                # Ensure current is a list
                if not isinstance(current, list):
                    raise TypeError(
                        f"Expected list at {path[:i]}, got {type(current).__name__}"
                    )
                while len(current) <= part:
                    current.append({})
                if not isinstance(current[part], (dict, list)):
                    current[part] = munch.munchify({})
                current = current[part]
            else:
                # Ensure current is a dict
                if not isinstance(current, dict):
                    raise TypeError(
                        f"Expected dict at {path[:i]}, got {type(current).__name__}"
                    )
                if part not in current or not isinstance(
                    current[part], (dict, list)
                ):
                    current[part] = munch.munchify({})
                current = current[part]

    def update(self, vmap: VariableMapType) -> Variables:
        def _deep_update(
            path: str,
            myd: dict,
            updates: dict,
        ) -> None:

            for key, value in updates.items():
                new_path = f"{path}.{key}" if path else key

                if (
                    key in myd
                    and isinstance(value, dict)
                    and isinstance(myd[key], dict)
                ):
                    _deep_update(new_path, myd[key], value)
                else:
                    self.set(new_path, value)

        _deep_update("", self._vmap, vmap)
        return self

    def interpolate(
        self,
        value: typing.Any,
        _seen: typing.Optional[set] = None,
    ) -> typing.Any:
        """
        Populate all variables in a value.

        :param value: The value to interpolate.

        :return: The interpolated value.
        """

        # Prevent infinite recursion.
        _seen = _seen or set()
        if id(value) in _seen:
            return value
        _seen.add(id(value))

        # Interpolate the value.
        if isinstance(value, dict):
            return {k: self.interpolate(v, _seen) for k, v in value.items()}

        if isinstance(value, list):
            return [self.interpolate(v, _seen) for v in value]

        if isinstance(value, tuple):
            return tuple(self.interpolate(v, _seen) for v in value)

        if isinstance(value, str):
            new_val = self._render(value, _seen)
            return new_val

        return value

    def _render(
        self,
        value: str,
        _seen: typing.Optional[set] = None,
    ) -> typing.Any:

        # Check if this is a pure variable name.
        found, obj = self.get(value)
        if found:
            return self.interpolate(obj, _seen)

        # This is the pattern
        pattern = r"(?<!\\){{\s*((?:[^\{\}]|\\\{|\\\})*?)\s*}}"

        # If the entire text is a single placeholder, return evaluation.
        full_match = re.fullmatch(pattern, value)
        if full_match:
            expr = full_match.group(1)
            return self._evaluate(expr)

        # Otherwise, replace all placeholders in the text.
        def replacer(match: re.Match) -> str:
            expr = match.group(1)
            return str(self._evaluate(expr))

        return re.sub(pattern, replacer, value)

    def _evaluate(self, expr: str) -> typing.Any:
        """Evaluate the expression safely, allowing only the vmap context."""
        # Replace escaped braces
        expr = expr.replace(r"\{", "{").replace(r"\}", "}")
        return evaluator(expr, self.vmap)


if __name__ == "__main__":

    v = Variables()

    v.set("result", {"a": 1, "b": {"name": "bob"}, "c": "{{ snoot }}"})

    v.set("chicken", "{{ result.c }}")
    v.set("chunks", "{{ chicken }}")
    v.set("snoot", 99)

    print(v.vmap)

    assert v.has("result.b.surname") == False

    v.update({"result": {"b": {"surname": "presley"}}})

    print(v.vmap)

    assert v.has("result.b") == True
    assert v.has("result.b.name") == True
    assert v.has("result.b.surname") == True
    assert v.has("result.b.steve") == False

    v.update({"result": {"b": 5}})

    print(v.vmap)

    assert v.has("result") == True
    assert v.has("result.c.steve") == False
    assert v.has("snoot") == True
    assert v.has("chunks") == True
    assert v.has("elvis") == False

    # Interpolate needs to be only one layer deep
    assert v.interpolate("{{ chunks }}") == "{{ chicken }}"
    assert v.interpolate("{{ result.b }}") == 5

    try:
        v.interpolate("{{ result.b.name }}")
        assert False
    except:
        pass

    try:
        val = v.interpolate("{{ snoop }}")
        assert False
    except:
        pass

    assert v.interpolate('{{ \\{ "elvis": 5 \\}["elvis"] + 5  }}') == 10

    class Test:
        def __init__(self):
            self.name: str = "elvis"
            self.profile: dict = {"age": 42}

    v.set("myclass.nesting.test", Test())

    print(v.vmap)

    assert v.has("myclass.nesting.test") == True
    assert v.has("myclass.nesting.test.name") == True
    assert v.has("myclass.nesting.test.profile['age']") == True
    assert v.has("myclass.nesting.test.profile['amber']") == False

    v.set("this", "this")

    crazy_string = """
I am {{ myclass.nesting.test.name }} and I am {{ myclass.nesting.test.profile['age'] }}
years old.
You're looking for {{ snoot }}.
The value of result.b is [{{ result.b }}].
A class renders as: [{{ myclass.nesting.test }}]
This = [{{ this }}]
"""
    string1 = v.interpolate(crazy_string)
    print(string1)

    str1 = "{{ snoot }} {{ snoot }} {{ f'\\{snoot\\}' + '\\{\\}' }}"
    print(v.interpolate(str1))

    print("Success.")

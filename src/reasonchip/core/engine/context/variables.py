##!/usr/bin/env python

from __future__ import annotations

import typing
import re

import munch

from pydantic import BaseModel

from dotty_dict import dotty, Dotty

from ruamel.yaml import YAML

from ... import exceptions as rex


VariableMapType = typing.Dict[str, typing.Any]


class Variables:


    def __init__(self, vmap: VariableMapType = {}) -> None:
        self._vmap: Dotty = dotty(vmap)


    @property
    def vmap(self) -> Dotty:
        return self._vmap


    @property
    def vdict(self) -> typing.Dict[str, typing.Any]:
        tmp = self.vmap

        flat_dict = {}
        for key, value in tmp.items():
            flat_dict[key] = value

        return flat_dict

    @property
    def vobj(self):
        return munch.munchify(self.vdict)


    def copy(self) -> Variables:
        v = Variables()
        v._vmap = self._vmap.copy()
        return v


    def load_file(self, filename: str):
        """
        Load variables from a file.

        :param filename: The file's name.
        """
        yml = YAML()
        with open(filename, 'r') as f:
            v = yml.load(f)
            if not v:
                return

            if not isinstance(v, dict):
                raise ValueError(f"Variable file must be a dictionary: {filename}")

            self.update(v)


    def has(self, key: str) -> bool:
        try:
            return key in self.vmap
        except:
            return False


    def get(self, key: str) -> typing.Any:
        return self.vmap.get(key, None)


    def set(self, key: str, value: typing.Any) -> Variables:
        self.vmap[key] = value
        return self


    def deep_has(self, key: str) -> typing.Tuple[bool, typing.Any]:
        new_key, rem = self._hunt(key)

        # No key to hunt.
        if not new_key:
            return (False, None)

        # There is something.
        obj = self.get(new_key)

        # Perfect match.
        if not rem:
            return (True, obj)

        # Now deep dive into the object.
        parts = rem.split('.')
        while parts:
            part = parts.pop(0)

            if hasattr(obj, part):
                obj = getattr(obj, part)

            elif isinstance(obj, dict):
                if part not in obj:
                    return (False, None)
                obj = obj.get(part, None)

            elif isinstance(obj, list) or isinstance(obj, tuple):
                try:
                    idx = int(part)
                    obj = obj[idx]
                except:
                    return (False, None)

            elif isinstance(obj, BaseModel):
                if part not in obj.model_fields:
                    return (False, None)
                obj = getattr(obj, part)

            else:
                print(f"************************************")
                print(f"We were looking for {key}")
                print(f"New key: {new_key}")
                print(f"Remaining: {rem}")
                print(f"Part: {part}")
                print(f"Parts: {parts}")
                print(f"Obj: {obj}")
                assert False, f"Unhandled type: {type(obj)}"


        return (True, obj)


    def deep_get(self, key: str) -> typing.Tuple[bool, typing.Any]:
        return self.deep_has(key)


    def update(self, vmap: VariableMapType) -> Variables:
        def _deep_update(dotty: Dotty, updates: dict) -> None:
            for key, value in updates.items():
                if isinstance(value, dict) and key in dotty and isinstance(dotty[key], dict):
                    # Recursively merge nested dicts
                    _deep_update(dotty[key], value)
                else:
                    dotty[key] = value

        _deep_update(self.vmap, vmap)
        return self


    def interpolate(self, value: typing.Any, _seen: typing.Optional[set] = None) -> typing.Any:
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
            found, obj = self.deep_get(value)
            if found:
                # This is a pure variable
                return self.interpolate(obj, _seen)

            new_value = self._render(value)
            if new_value != value:
                return self.interpolate(new_value, _seen)

            return new_value

        return value


    def _render(self, text: str) -> typing.Any:
        pattern = r"{{\s*((?:[^\{\}]|\\\{|\\\})*?)\s*}}"

        # If the entire text is a single placeholder, evaluate and return
        # the native result.
        full_match = re.fullmatch(pattern, text)
        if full_match:
            expr = full_match.group(1)
            return self._evaluate(expr)

        # Otherwise, replace all placeholders in the text.
        def replacer(match: re.Match) -> str:
            expr = match.group(1)
            return str(self._evaluate(expr))

        return re.sub(pattern, replacer, text)


    def _evaluate(self, expr: str) -> typing.Any:
        """Evaluate the expression safely, allowing only the vobj context."""
        # Replace escaped braces
        expr = expr.replace(r"\{", "{").replace(r"\}", "}")

        # Evaluate the expression in a restricted environment
        result = eval(expr, {"__builtins__": {}}, self.vobj)
        return result


    def _hunt(self, key: str) -> typing.Tuple[str, str]:
        if self.has(key):
            return (key, "")

        # Hunt backwards through the key to find the first key that exists.
        parts = key.split('.')

        remaining = []
        while parts:
            fname = '.'.join(parts)
            if self.has(fname):
                break

            remaining.insert(0, parts.pop())

        return ('.'.join(parts), '.'.join(remaining))



if __name__ == "__main__":

    v = Variables()

    v.set("result", { 'a': 1, 'b': { 'name': 'bob' }, 'c': "{{ snoot }}" })

    v.set("chicken", "{{ result.c }}")
    v.set("chunks", "{{ chicken }}")
    v.set("snoot", 99)

    print(v.vmap)

    assert v.has("result.b.surname") == False

    v.update({ 'result': { 'b': { 'surname': 'presley' }}})

    print(v.vmap)

    assert v.has("result.b") == True
    assert v.has("result.b.name") == True
    assert v.has("result.b.surname") == True
    assert v.has("result.b.steve") == False

    v.update({ 'result': { 'b': 5 }})

    print(v.vmap)

    assert v.has("result") == True
    assert v.has("result.c.steve") == False
    assert v.has("snoot") == True
    assert v.has("chunks") == True
    assert v.has("elvis") == False

    assert v.interpolate("{{ chunks }}") == 99
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


    class Test:
        def __init__(self):
            self.name: str = "elvis"
            self.profile: dict = { 'age': 42 }

    v.set("myclass.nesting.test", Test())

    print(v.vmap)

    assert v.has("myclass.nesting.test") == True
    assert v.has("myclass.nesting.test.name") == False
    assert v.has("myclass.nesting.test.profile.age") == False

    assert v.deep_has("myclass.nesting.test.name")[0] == True
    assert v.deep_has("myclass.nesting.test.profile.age")[0] == True
    assert v.deep_has("myclass.nesting.test.profile.amber")[0] == False

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



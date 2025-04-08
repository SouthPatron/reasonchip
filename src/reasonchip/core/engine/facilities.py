from __future__ import annotations

import typing



class Facilities:

    _instance: typing.Optional[Facilities] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance



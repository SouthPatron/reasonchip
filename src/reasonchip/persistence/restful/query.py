from __future__ import annotations
import typing


class Query:

    def __init__(
        self,
        **filters,
    ):
        self._filters: typing.Dict[str, typing.Any] = filters
        self._ordering: typing.Optional[str] = None
        self._limit: typing.Optional[int] = None
        self._offset: typing.Optional[int] = None

    def search(self, term: str) -> Query:
        self._filters["search"] = term
        return self

    def filter(self, **kwargs) -> Query:
        self._filters.update(kwargs)
        return self

    def order_by(self, ordering: str) -> Query:
        self._ordering = ordering
        return self

    def limit(self, limit: int) -> Query:
        self._limit = limit
        return self

    def offset(self, offset: int = 0) -> Query:
        self._offset = offset
        return self

    def to_params(self) -> dict:
        params = self._filters.copy()

        if self._ordering:
            params["ordering"] = self._ordering

        if self._limit is not None:
            params["limit"] = self._limit

        if self._offset is not None:
            params["offset"] = self._offset

        return params

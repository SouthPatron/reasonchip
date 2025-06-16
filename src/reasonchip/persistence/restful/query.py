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

    def filter(self, **kwargs):
        self._filters.update(kwargs)

    def order_by(self, ordering: str):
        self._ordering = ordering

    def limit(self, limit: int):
        self._limit = limit

    def offset(self, offset: int = 0):
        self._offset = offset

    def to_params(self) -> dict:
        params = self._filters.copy()

        if self._ordering:
            params["ordering"] = self._ordering

        if self._limit is not None:
            params["limit"] = self._limit

        if self._offset is not None:
            params["offset"] = self._offset

        return params

import sys
import typing
import inspect
import logging
import threading
import collections.abc


class Error:
    """Namespace for functionalities related to runtime erros"""

    @staticmethod
    def exit(message: str, code = 1) -> typing.NoReturn:
        logging.error(message)
        sys.exit(code)


class Singleton(type):
    # From https://refactoring.guru/design-patterns/singleton/python/example
    """Metaclass to define singletons"""

    _instances: dict["Singleton", typing.Any] = {}

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        if self not in self._instances:
            self._instances[self] = super().__call__(*args, **kwargs)

        return self._instances[self]


_Return = typing.TypeVar("_Return")
_Params = typing.ParamSpec("_Params")

_Coroutine = collections.abc.Callable[
    _Params,
    collections.abc.Coroutine[typing.Any, typing.Any, _Return]
]

Callbackable = (
    collections.abc.Callable[_Params, _Return] |
    _Coroutine[_Params, _Return] |
    None
)

class Callback(typing.Generic[_Params, _Return]):
    """Wrapper for optional callables or coroutine functions"""

    def __init__(self, handler: Callbackable[_Params, _Return] = None) -> None:
        self.handler = handler

    async def __call__(self, *args: _Params.args, **kwargs: _Params.kwargs):
        if self.handler is None:
            return None

        if inspect.iscoroutinefunction(self.handler):
            coroutine = typing.cast(_Coroutine[_Params, _Return], self.handler)
            return await coroutine(*args, **kwargs)

        callable = typing.cast(
            collections.abc.Callable[_Params, _Return],
            self.handler
        )

        return callable(*args, **kwargs)

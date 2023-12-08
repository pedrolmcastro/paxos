import sys
import typing
import logging
import threading


class Error:
    """Namespace for functionality related to runtime erros"""


    @staticmethod
    def exit(message: str, code = 1) -> typing.NoReturn:
        logging.error(message)
        sys.exit(code)


class Singleton(type):
    """Metaclass to define thread-safe singletons"""
    # From https://refactoring.guru/design-patterns/singleton/python/example#example-1


    _lock = threading.Lock()
    _instances: dict["Singleton", typing.Any] = {}


    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        with self._lock:
            if self not in self._instances:
                self._instances[self] = super().__call__(*args, **kwargs)

        return self._instances[self]

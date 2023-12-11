import typing


class Singleton(type):
    # From https://refactoring.guru/design-patterns/singleton/python/example
    """Metaclass to define singletons"""

    _instances: dict["Singleton", typing.Any] = {}

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        if self not in self._instances:
            self._instances[self] = super().__call__(*args, **kwargs)

        return self._instances[self]

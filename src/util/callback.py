import typing
import inspect
import collections.abc


_Params = typing.ParamSpec("_Params")

_Coroutine = collections.abc.Callable[
    _Params,
    collections.abc.Coroutine[typing.Any, typing.Any, None]
]

Handler = collections.abc.Callable[_Params, None] | _Coroutine[_Params] | None


class Callback(typing.Generic[_Params]):
    """Wrapper for optional callables or coroutine functions returning None"""

    def __init__(self, handler: Handler[_Params] = None) -> None:
        self.handler = handler

    def __bool__(self) -> bool:
        return self.handler is not None

    async def __call__(
        self,
        *args: _Params.args,
        **kwargs: _Params.kwargs
    ) -> None:
        if self.handler is None:
            return

        if inspect.iscoroutinefunction(self.handler):
            coroutine = typing.cast(_Coroutine[_Params], self.handler)
            return await coroutine(*args, **kwargs)

        callable = typing.cast(
            collections.abc.Callable[_Params, None],
            self.handler,
        )

        callable(*args, **kwargs)

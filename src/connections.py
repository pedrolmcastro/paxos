import typing
import asyncio
import inspect
import logging
import threading

from host import Host
from connection import Connection


DisconnectEvent = (
    typing.Callable[[int], typing.Coroutine[typing.Any, typing.Any, int]] |
    typing.Callable[[int], None] |
    None
)


class Connections:
    """Container of multiple Connection objects"""


    def __init__(
        self,
        connections: set[Connection],
        on_disconnect: DisconnectEvent = None,
    ) -> None:
        self._lock = threading.Lock()
        self._connections = connections
        self._on_disconnect = on_disconnect

    @classmethod
    async def connect(
        cls,
        hosts: typing.Iterable[Host],
        timeouts: typing.Iterable[float],
        on_disconnect: DisconnectEvent = None,
    ) -> "Connections":
        tasks = [Connection.connect(host, timeouts) for host in hosts]
        connections: set[Connection] = set()

        for coroutine in asyncio.as_completed(tasks):
            try:
                connections.add(await coroutine)
            except Exception as exception:
                logging.warning(str(exception))

        return cls(connections, on_disconnect)


    async def close(self) -> None:
        await asyncio.gather(
            *(connection.close() for connection in self._connections)
        )

        with self._lock:
            self._connections = set()


    async def __aenter__(self) -> "Connections":
        return self

    async def __aexit__(self, type, value, traceback) -> None:
        await self.close()


    def __len__(self) -> int:
        with self._lock:
            return len(self._connections)


    async def _disconnect(self, connection: Connection):
        with self._lock:
            self._connections.discard(connection)
            length = len(self._connections)

        if inspect.iscoroutinefunction(self._on_disconnect):
            await self._on_disconnect(length)
        elif callable(self._on_disconnect):
            self._on_disconnect(length)


    async def broadcast(self, data: bytes) -> None:
        async def task(connection: Connection, data: bytes):
            try:
                await connection.send(data)
            except Exception as exception:
                logging.warning(f"Failed to send message: {exception}")
                await self._disconnect(connection)

        await asyncio.gather(
            *(task(connection, data) for connection in self._connections)
        )

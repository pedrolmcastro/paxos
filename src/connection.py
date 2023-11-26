import uuid
import asyncio
import logging
import threading
from typing import Callable

from host import Host



class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer
        self._id = uuid.uuid4()

    @classmethod
    async def connect(cls, host: Host, timeouts: list[float]) -> "Connection":
        address = host.info[0]
        fails = 0

        for timeout in timeouts:
            await asyncio.sleep(timeout)

            try:
                reader, writer = await asyncio.open_connection(address.address, address.port.number)
                return cls(reader, writer)
            except Exception:
                fails += 1
                logging.warning(f"Failed to connect to {host} {fails} time(s)")

        raise ConnectionError(f"Failed to connect to {host} after {fails} attempts")


    async def close(self) -> None:
        self._writer.close()
        await self._writer.wait_closed()


    async def __aenter__(self) -> "Connection":
        return self

    async def __aexit__(self, typ, value, traceback) -> None:
        await self.close()


    def __hash__(self) -> int:
        return self._id.int


    async def send(self, data: bytes) -> None:
        self._writer.write(data)
        await self._writer.drain()


class Manager:
    def __init__(
        self,
        connections: set[Connection],
        ondisconnect: Callable[[int], None] | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._connections = connections
        self._ondisconnect = ondisconnect

    @classmethod
    async def connect(
        cls,
        hosts: list[Host],
        timeouts: list[float],
        ondisconnect: Callable[[int], None] | None = None,
    ) -> "Manager":
        tasks = [Connection.connect(host, timeouts) for host in hosts]
        connections: set[Connection] = set()

        for coroutine in asyncio.as_completed(tasks):
            try:
                connections.add(await coroutine)
            except Exception as exception:
                logging.warning(str(exception))

        return cls(connections, ondisconnect)


    async def close(self) -> None:
        await asyncio.gather(*(connection.close() for connection in self._connections))

        with self._lock:
            self._connections = set()


    async def __aenter__(self) -> "Manager":
        return self

    async def __aexit__(self, typ, value, traceback) -> None:
        await self.close()


    def __len__(self) -> int:
        with self._lock:
            return len(self._connections)


    def _disconnect(self, connection: Connection):
        with self._lock:
            self._connections.discard(connection)

            if self._ondisconnect is not None:
                self._ondisconnect(len(self._connections))


    async def broadcast(self, data: bytes) -> None:
        async def task(connection: Connection, data: bytes):
            try:
                await connection.send(data)
            except Exception as exception:
                logging.warning(f"Failed to send message: {exception}")
                self._disconnect(connection)

        await asyncio.gather(*(task(connection, data) for connection in self._connections))

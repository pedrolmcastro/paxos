import asyncio
import logging

from host import Host


class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    @classmethod
    async def connect(cls, host: Host, timeouts: list[float] | None = None) -> "Connection":
        if timeouts is None:
            timeouts = []

        address = host.info[0]
        fails = 0

        for timeout in timeouts:
            try:
                reader, writer = await asyncio.open_connection(address.address, address.port.number)
                return cls(reader, writer)
            except Exception as exception:
                fails += 1
                logging.warning(f"Failed to connect to {host} {fails} time(s): {exception}")

            await asyncio.sleep(timeout)

        # In this last attempt, any open_connection() raised exception is not caught
        reader, writer = await asyncio.open_connection(address.address, address.port.number)
        return cls(reader, writer)


    async def close(self):
        self._writer.close()
        await self._writer.wait_closed()


    async def __aenter__(self) -> "Connection":
        return self

    async def __aexit__(self, typ, value, traceback) -> None:
        await self.close()


class Manager:
    def __init__(self, connections: list[Connection]) -> None:
        self._connections = connections

    @classmethod
    async def connect(cls, hosts: list[Host], timeouts: list[float] | None = None) -> "Manager":
        if timeouts is None:
            timeouts = []

        tasks = [Connection.connect(host, timeouts) for host in hosts]
        connections: list[Connection] = []

        for coroutine in asyncio.as_completed(tasks):
            try:
                connection = await coroutine
                connections.append(connection)
            except Exception as exception:
                attempts = len(timeouts) + 1
                logging.warning(f"Failed to connect to a host: {exception}")

        return cls(connections)


    async def close(self):
        await asyncio.gather(*(connection.close() for connection in self._connections))


    async def __aenter__(self) -> "Manager":
        return self

    async def __aexit__(self, typ, value, traceback) -> None:
        await self.close()


    def __len__(self) -> int:
        return len(self._connections)

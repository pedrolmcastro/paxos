import asyncio
import logging

from host import Host


class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

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


    async def send(self, data: bytes) -> None:
        self._writer.write(data)
        await self._writer.drain()


class Manager:
    def __init__(self, connections: list[Connection]) -> None:
        self._connections = connections

    @classmethod
    async def connect(cls, hosts: list[Host], timeouts: list[float]) -> "Manager":
        tasks = [Connection.connect(host, timeouts) for host in hosts]
        connections: list[Connection] = []

        for coroutine in asyncio.as_completed(tasks):
            try:
                connections.append(await coroutine)
            except Exception as exception:
                logging.warning(str(exception))

        return cls(connections)


    async def close(self) -> None:
        await asyncio.gather(*(connection.close() for connection in self._connections))


    async def __aenter__(self) -> "Manager":
        return self

    async def __aexit__(self, typ, value, traceback) -> None:
        await self.close()


    def __len__(self) -> int:
        return len(self._connections)


    async def broadcast(self, data: bytes) -> None:
        await asyncio.gather(*(connection.send(data) for connection in self._connections))

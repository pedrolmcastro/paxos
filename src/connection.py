import uuid
import typing
import asyncio
import logging

from host import Host


class Connection:
    """Wrapper for asyncio.StreamWriter to manage a single connection"""


    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self._writer = writer

        # Random ID to make Connection hashable and usable in a set
        self._id = uuid.uuid4()

    @classmethod
    async def connect(
        cls,
        host: Host,
        timeouts: typing.Iterable[float]
    ) -> "Connection":
        address = host.info[0]
        fails = 0

        for timeout in timeouts:
            try:
                _, writer = await asyncio.open_connection(
                    address.address,
                    address.port.number,
                )

                return cls(writer)
            except Exception:
                fails += 1

                logging.warning(
                    f"Failed to connect to '{host}': {fails} time(s)"
                )

            await asyncio.sleep(timeout)

        # If this fails the exception raised will not be caught
        _, writer = await asyncio.open_connection(
            address.address,
            address.port.number,
        )

        return cls(writer)


    async def close(self) -> None:
        self._writer.close()
        await self._writer.wait_closed()


    async def __aenter__(self) -> "Connection":
        return self

    async def __aexit__(self, type, value, traceback) -> None:
        await self.close()


    def __hash__(self) -> int:
        return self._id.int


    async def send(self, data: bytes) -> None:
        self._writer.write(data)
        await self._writer.drain()

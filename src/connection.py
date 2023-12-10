import uuid
import typing
import asyncio
import logging
import functools
import collections.abc

import host
import message
import callback


Delays = collections.abc.Iterable[float]
Native = tuple[asyncio.StreamReader, asyncio.StreamWriter]
Handshake = callback.Handler[[asyncio.StreamReader, asyncio.StreamWriter]]


async def connect(
    host: host.Host,
    delays: Delays,
    handshake: Handshake = None,
) -> Native:
    """Creates a single connection"""


    address = host.addresses[0]
    fails = 0

    for delay in delays:
        await asyncio.sleep(delay)

        try:
            reader, writer = await asyncio.open_connection(
                address.address,
                address.port.number,
            )

            await callback.Callback(handshake)(reader, writer)
            return reader, writer
        except Exception:
            fails += 1
            logging.warning(f"Failed to connect to '{host}': {fails} time(s)")

    raise ConnectionError(f"Failed to connect to '{host}'")

async def connectall(
    hosts: collections.abc.Iterable[host.Host],
    delays: Delays,
    handshake: Handshake = None,
) -> list[Native]:
    """Creates multiple connections"""

    tasks = [connect(host, delays, handshake) for host in hosts]
    connections: list[Native] = []

    for future in asyncio.as_completed(tasks):
        try:
            connections.append(await future)
        except Exception as exception:
            logging.warning(str(exception))

    return connections


class Connection:
    """Wrapper of asyncio streams to manage a single connection"""

    OnFail = callback.Callback[[]]
    OnReceive = callback.Callback[[message.Message]]

    def __init__(self) -> None:
        # Connection streams
        self._writer: asyncio.StreamWriter | None = None
        self._reader: asyncio.StreamReader | None = None
        self._associated: asyncio.StreamWriter | None = None # reader lifetime

        # Message queues and events
        self._failed = asyncio.Event()
        self._sending: asyncio.Queue[message.Message] = asyncio.Queue()
        self._received: asyncio.Queue[message.Message] = asyncio.Queue()

        # Background tasks
        self._sender: asyncio.Task[None] | None = None
        self._receiver: asyncio.Task[None] | None = None
        self._aborter = asyncio.create_task(self._abort())
        self._notifier = asyncio.create_task(self._notifiy())

        # Callbacks
        self._on_fail = self.OnFail()
        self._on_receive = self.OnReceive()

    async def close(self) -> None:
        """Closes the current connection"""
        await self.set_reader(None)
        await self.set_writer(None)
        self._aborter.cancel()

    async def send(self, message: message.Message) -> None:
        """Enqueues a message to be sent"""
        await self._sending.put(message)

    def on_receive(self, handler: callback.Handler[[message.Message]]):
        """Sets the callback for received messages"""
        self._on_receive.handler = handler

    def on_fail(self, handler: callback.Handler[[]]):
        """Sets the callback for failed operations"""
        self._on_fail.handler = handler

    async def set_writer(self, writer: asyncio.StreamWriter | None) -> None:
        """Sets a new writer stream and closes the previous"""

        if self._writer is writer:
            return

        # Consume the queued sends
        if self._writer is not None:
            await self._sending.join()

        # Cancel the previously associated sender task
        if self._sender is not None:
            self._sender.cancel()
            self._sender = None

        # Close the previous writer
        if self._writer is not None and self._writer is not self._associated:
            self._writer.close()
            await self._writer.wait_closed()

        self._writer = writer

        # Associate a new sender task
        if self._writer is not None:
            self._sender = asyncio.create_task(self._send())

    async def set_reader(
        self,
        reader: asyncio.StreamReader | None,
        associated: asyncio.StreamWriter | None = None
    ) -> None:
        """Sets a new reader stream and closes the previous"""

        if self._reader is reader:
            return

        # Cancel the previously associated receiver task
        if self._receiver is not None:
            self._receiver.cancel()
            self._receiver = None

        await self._received.join()

        # Close the previous writer associated to the reader lifetime
        if (
            self._associated is not None and
            self._associated is not self._writer
        ):
            self._associated.close()
            await self._associated.wait_closed()

        self._reader = reader
        self._associated = associated

        # Associate a new receiver task
        if self._reader is not None:
            self._receiver = asyncio.create_task(self._receive())

    async def _send(self) -> None:
        """Waits in the queue for a message to be sent and consumes it"""
        writer = typing.cast(asyncio.StreamWriter, self._writer)

        while True:
            dequeued = await self._sending.get()

            try:
                await message.send(writer, dequeued)
            except Exception:
                self._failed.set()

            self._sending.task_done()

    async def _receive(self) -> None:
        """Waits for messages and populates the received queue"""
        reader = typing.cast(asyncio.StreamReader, self._reader)

        while True:
            try:
                received = await message.receive(reader)
            except Exception:
                return self._failed.set()

            await self._received.put(received)

    async def _notifiy(self) -> None:
        """Waits in the queue for a received message and consumes it"""

        while True:
            dequeued = await self._received.get()
            await self._on_receive(dequeued)
            self._received.task_done()

    async def _abort(self) -> None:
        """Waits for the failed event and closes the connection if it happens"""
        await self._failed.wait()
        await self._on_fail()
        await self.close()

    async def __aenter__(self) -> "Connection":
        return self

    async def __aexit__(self, type, value, traceback) -> None:
        await self.close()


class Map(collections.abc.MutableMapping):
    """Mapping container from uid to connection"""

    OnReceive = callback.Callback[[uuid.UUID, message.Message]]

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, Connection] = {}
        self._on_receive: Map.OnReceive = callback.Callback()

    async def close(self) -> None:
        """Closes all the contained connections"""
        uids = list(iter(self)) # Allow removing while iterating
        await asyncio.gather(*(self.disconnect(uid) for uid in uids))

    async def disconnect(self, uid: uuid.UUID) -> None:
        """Closes the connection with the uid"""
        await self[uid].close()
        del self[uid]

    async def send(self, uid: uuid.UUID, message: message.Message) -> None:
        """Sends the message to the connection with the uid"""
        await self[uid].send(message)

    async def broadcast(self, message: message.Message) -> None:
        """Sends the message to all the contained connections"""
        await asyncio.gather(*(self.send(uid, message) for uid in self))

    def on_receive(
        self,
        handler: callback.Handler[[uuid.UUID, message.Message]]
    ) -> None:
        """Sets the callback for received messages"""
        self._on_receive.handler = handler

    def __getitem__(self, uid: uuid.UUID) -> Connection:
        return self._connections[uid]

    def __setitem__(self, uid: uuid.UUID, connection: Connection) -> None:
        async def on_fail() -> None:
            if uid in self:
                logging.warning(f"Lost connection to host '{uid}'")
                del self[uid]

        async def on_receive(message: message.Message) -> None:
            await self._on_receive(uid, message)

        connection.on_fail(on_fail)
        connection.on_receive(on_receive)

        self._connections[uid] = connection

    def __delitem__(self, uid: uuid.UUID) -> None:
        del self._connections[uid]

    def __iter__(self) -> typing.Iterator[uuid.UUID]:
        return iter(self._connections)

    def __len__(self) -> int:
        return len(self._connections)

    async def __aenter__(self) -> "Map":
        return self

    async def __aexit__(self, type, value, traceback) -> None:
        await self.close()

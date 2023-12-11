import uuid
import typing
import asyncio
import collections.abc

from util import callback

from network import host
from network import message


Delays = collections.abc.Iterable[float]
OnFail = callback.Handler[[Exception, host.Host, int]]
Native = tuple[asyncio.StreamReader, asyncio.StreamWriter]
Handshake = callback.Handler[[asyncio.StreamReader, asyncio.StreamWriter]]


async def connect(
    host: host.Host,
    delays: Delays,
    handshake: Handshake = None,
    on_fail: OnFail = None,
) -> Native:
    """Creates a single connection"""

    # Convert the handlers to callbacks
    handshake = callback.Callback(handshake)
    on_fail = callback.Callback(on_fail)

    address = host.addresses[0]
    fails = 0

    for delay in delays:
        await asyncio.sleep(delay)

        try:
            reader, writer = await asyncio.open_connection(
                address.address,
                address.port.number,
            )

            await handshake(reader, writer)
            return reader, writer
        except Exception as exception:
            fails += 1
            await on_fail(exception, host, fails)

    raise ConnectionError(f"Failed to connect to {host}")

async def connectall(
    hosts: collections.abc.Iterable[host.Host],
    delays: Delays,
    handshake: Handshake = None,
    on_fail: OnFail = None,
) -> list[Native]:
    """Creates multiple connections"""

    tasks = [connect(host, delays, handshake, on_fail) for host in hosts]
    connections: list[Native] = []

    for future in asyncio.as_completed(tasks):
        try:
            connections.append(await future)
        except ConnectionError:
            pass

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

        # Queues and events
        self._failed = asyncio.Event()
        self._sending: asyncio.Queue[message.Message] = asyncio.Queue()
        self._received: asyncio.Queue[message.Message] = asyncio.Queue()

        # Tasks
        self._sender: asyncio.Task[None] | None = None
        self._receiver: asyncio.Task[None] | None = None
        self._notifier: asyncio.Task[None] | None = None
        self._aborter = asyncio.create_task(self._abort())

        # Callbacks
        self._on_fail = self.OnFail()
        self._on_receive = self.OnReceive()

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

    async def send(self, message: message.Message) -> None:
        """Enqueues a message to be sent"""
        await self._sending.put(message)

    async def on_receive(
        self,
        handler: callback.Handler[[message.Message]],
    ) -> None:
        """Sets the callback for received messages"""

        if self._notifier is not None:
            # Consume the queued receives
            await self._received.join()

            # Cancel the previously associated notifier task
            self._notifier.cancel()
            self._notifier = None

        self._on_receive.handler = handler

        # Associate a new notifier task
        if self._on_receive:
            self._notifier = asyncio.create_task(self._notifiy())

    def on_fail(self, handler: callback.Handler[[]]) -> None:
        """Sets the callback for failed operations"""
        self._on_fail.handler = handler

    async def close(self) -> None:
        """Closes the current connection"""
        await self.set_reader(None)
        await self.set_writer(None)
        await self.on_receive(None)
        self._aborter.cancel()

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


class Map(collections.abc.Sized, collections.abc.Container):
    """Mapping container from uid to connection"""

    OnFail = callback.Callback[[uuid.UUID]]
    OnReceive = callback.Callback[[uuid.UUID, message.Message]]

    _Received = tuple[uuid.UUID, message.Message]

    def __init__(self) -> None:
        # Connections
        self._connections: dict[uuid.UUID, Connection] = {}

        # Queues
        self._received: asyncio.Queue[Map._Received] = asyncio.Queue()

        # Tasks
        self._notifier: asyncio.Task[None] | None = None

        # Callbacks
        self._on_fail = self.OnFail()
        self._on_receive = self.OnReceive()

    async def set_writer(
        self,
        uid: uuid.UUID,
        writer: asyncio.StreamWriter | None,
    ) -> None:
        """Sets the writer of the connection with the uid"""

        if uid not in self:
            await self._add(uid)

        await self._connections[uid].set_writer(writer)

    async def set_reader(
        self,
        uid: uuid.UUID,
        reader: asyncio.StreamReader | None,
        associated: asyncio.StreamWriter | None = None,
    ) -> None:
        """Sets the reader of the connection with the uid"""

        if uid not in self:
            await self._add(uid)

        await self._connections[uid].set_reader(reader, associated)

    async def send(self, uid: uuid.UUID, message: message.Message) -> None:
        """Sends the message to the connection with the uid"""
        await self._connections[uid].send(message)

    async def broadcast(self, message: message.Message) -> None:
        """Sends the message to all the connections"""
        await asyncio.gather(
            *(self.send(uid, message) for uid in self._connections)
        )

    async def on_receive(
        self,
        handler: callback.Handler[[uuid.UUID, message.Message]],
    ) -> None:
        """Sets the callback for received messages"""

        if self._notifier is not None:
            # Consume the queued receives
            await self._received.join()

            # Cancel the previously associated notifier task
            self._notifier.cancel()
            self._notifier = None

        self._on_receive.handler = handler

        # Associate a new notifier task
        if self._on_receive:
            self._notifier = asyncio.create_task(self._notifiy())

    def on_fail(self, handler: callback.Handler[[uuid.UUID]]) -> None:
        """Sets the callback for failed operations"""
        self._on_fail.handler = handler

    async def close(self, uid: uuid.UUID) -> None:
        """Closes the connection with the uid"""
        await self._connections[uid].close()
        del self._connections[uid]

    async def clear(self) -> None:
        """Closes all the connections"""

        uids = list(self._connections.keys()) # Allow removing while iterating
        await asyncio.gather(*(self.close(uid) for uid in uids))

        await self.on_receive(None)

    async def _add(self, uid: uuid.UUID) -> None:
        """Add a new connection with the uuid to the map"""

        async def on_fail() -> None:
            if uid in self:
                del self._connections[uid]
                await self._on_fail(uid)

        async def on_receive(message: message.Message) -> None:
            await self._received.put((uid, message))

        connection = Connection()
        connection.on_fail(on_fail)
        await connection.on_receive(on_receive)

        self._connections[uid] = connection

    async def _notifiy(self) -> None:
        """Waits in the queue for a received message and consumes it"""

        while True:
            dequeued = await self._received.get()
            await self._on_receive(*dequeued)
            self._received.task_done()

    def __len__(self) -> int:
        return len(self._connections)

    def __contains__(self, key: object) -> bool:
        return key in self._connections

    async def __aenter__(self) -> "Map":
        return self

    async def __aexit__(self, type, value, traceback) -> None:
        await self.clear()

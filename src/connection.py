import typing
import asyncio

from message import Message
from util import Callback, Callbackable


class Connection:
    """Wrapper of asyncio streams to manage a single connection"""

    def __init__(self) -> None:
        # Connection streams
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

        # Message queues
        self._sending: asyncio.Queue[Message.Any] = asyncio.Queue()
        self._received: asyncio.Queue[Message.Any] = asyncio.Queue()

        # Background tasks
        self._sender: asyncio.Task[None] | None = None
        self._receiver: asyncio.Task[None] | None = None
        self._notifier = asyncio.create_task(self._notifiy())

        # Callbacks
        self._onreceive: Callback[[Message.Any], None] = Callback()

    async def close(self) -> None:
        """Closes the current connection"""

        await self._received.join()

        self.reader = None
        self._onreceive.handler = None
        self._received = asyncio.Queue()

        if self._writer is not None:
            await self._sending.join()

            self._writer.close()
            await self._writer.wait_closed()

        self.writer = None
        self._sending = asyncio.Queue()

    async def send(self, message: Message.Any) -> None:
        """Enqueues a message to be sent"""
        await self._sending.put(message)

    def onreceive(self, handler: Callbackable[[Message.Any], None]):
        """Sets the callback for received messages"""
        self._onreceive.handler = handler

    @property
    def reader(self):
        return self._reader

    @reader.setter
    def reader(self, reader: asyncio.StreamReader | None) -> None:
        if self._receiver is not None:
            self._receiver.cancel()
            self._receiver = None

        self._reader = reader

        if self._reader is not None:
            self._receiver = asyncio.create_task(self._receive())

    @property
    def writer(self):
        return self._writer

    @writer.setter
    def writer(self, writer: asyncio.StreamWriter | None) -> None:
        if self._sender is not None:
            self._sender.cancel()
            self._sender = None

        self._writer = writer

        if self._writer is not None:
            self._sender = asyncio.create_task(self._send())

    async def _receive(self) -> None:
        """Task that waits for messages and populates the received queue"""
        reader = typing.cast(asyncio.StreamReader, self._reader)

        while True:
            try:
                encoded = await reader.readexactly(Message.Header.SIZE)
                header = Message.Header.decode(encoded)

                payload = await reader.readexactly(header.length)
                message = Message.decode(header, payload)

                await self._received.put(message)
            except Exception:
                pass # TODO

    async def _notifiy(self) -> None:
        """Waits in the queue for a received message and consumes it"""

        while True:
            try:
                message = await self._received.get()
                await self._onreceive(message)

                self._received.task_done()
            except Exception:
                pass # TODO

    async def _send(self) -> None:
        """Waits in the queue for a message to be sent and consumes it"""
        writer = typing.cast(asyncio.StreamWriter, self._writer)

        while True:
            try:
                message = await self._sending.get()

                writer.write(Message.encode(message))
                await writer.drain()

                self._sending.task_done()
            except Exception:
                pass # TODO

    async def __aenter__(self) -> "Connection":
        return self

    async def __aexit__(self, type, value, traceback) -> None:
        await self.close()

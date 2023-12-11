import uuid
import asyncio
import logging
import collections.abc

from util import error
from util import callback

from network import host
from network import message
from network import connection

from app import security


class Mediator:
    def __init__(self, hosts: collections.abc.Collection[host.Host]) -> None:
        # Configuration
        self._hosts = hosts
        self._majority = len(self._hosts) // 2 + 1

        # Server and events
        self._done = asyncio.Event()
        self._server: asyncio.Server | None = None

        # Connection maps
        self._clients = connection.Map()
        self._servers = connection.Map()
        self._clients.on_fail(self._on_client_fail)
        self._servers.on_fail(self._on_server_fail)

        # Callbacks
        self._on_receive = connection.Map.OnReceive()

    async def start(
        self,
        port: host.Port,
        delays: connection.Delays,
        handler: callback.Handler[[uuid.UUID, message.Message]],
    ) -> None:
        """Starts the server"""

        self._on_receive.handler = handler

        await self._clients.on_receive(self._receive)
        await self._servers.on_receive(self._receive)

        try:
            self._server = await asyncio.start_server(
                self._greet,
                port = port.number,
                start_serving = True,
            )
        except Exception:
            error.exit(f"Failed to open server on port: '{port}'")

        await connection.connectall(
            self._hosts,
            delays,
            self._handshake,
            self._on_connect_fail
        )

        if len(self._servers) < self._majority:
            error.exit("Failed to connect to the majority of servers")

        logging.info("Server started")

    async def send(self, uid: uuid.UUID, message: message.Message) -> None:
        """Sends the message to the client or server with the uid"""

        if uid in self._servers:
            await self._servers.send(uid, message)
        else:
            await self._clients.send(uid, message)

    async def broadcast(self, message: message.Message) -> None:
        """Sends the message to all the connected servers"""
        await self._servers.broadcast(message)

    async def done(self) -> None:
        await self._done.wait()

    async def close(self):
        await self._clients.clear()
        await self._servers.clear()

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

        logging.info("Server closed")
        self._done.set()

    @property
    def majority(self) -> int:
        return self._majority

    async def _handshake(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handshake performed between servers"""

        await message.send(writer, message.Server(
            uid = security.Context().uid.int,
        ))

        response = await message.receive(reader)

        if not isinstance(response, message.Server):
            raise ValueError(f"Unexpected response type: {type(response)}")

        if not security.authenticate(response):
            raise ValueError(f"Authentication failed")

        await self._servers.set_writer(uuid.UUID(int = response.uid), writer)

    async def _greet(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Initial message exchange with new clients"""

        async def fail(writer: asyncio.StreamWriter, reason: str) -> None:
            writer.close()
            await writer.wait_closed()
            logging.warning(f"Failed greeting: {reason}")

        try:
            received = await message.receive(reader)
        except Exception as exception:
            return await fail(writer, str(exception))

        if (
            isinstance(received, security.Authenticated) and
            not security.authenticate(received)
        ):
            reason = "Authentication failed"

            try:
                await message.send(writer, message.Denied(reason = reason))
            finally:
                return await fail(writer, reason)

        match received:
            case message.Server():
                try:
                    await message.send(writer, message.Server(
                        uid = security.Context().uid.int,
                    ))
                except Exception as exception:
                    return await fail(writer, str(exception))

                uid = uuid.UUID(int = received.uid)
                await self._servers.set_reader(uid, reader, writer)
                logging.debug(f"Successfull server greeting: '{uid}'")

            case message.Client():
                try:
                    await message.send(writer, message.Acknowledge())
                except Exception as exception:
                    return await fail(writer, str(exception))

                uid = uuid.uuid4()
                await self._clients.set_writer(uid, writer)
                await self._clients.set_reader(uid, reader, writer)
                logging.debug(f"Successfull client greeting: '{uid}'")

            case _:
                reason = f"Unexpected greeting message: '{type(received)}'"

                try:
                    await message.send(writer, message.Denied(reason = reason))
                finally:
                    return await fail(writer, reason)

    async def _receive(
        self,
        sender: uuid.UUID,
        received: message.Message
    ) -> None:
        """Callback for received messages"""

        logging.debug(f"Message from '{sender}': {received}")

        if (
            isinstance(received, security.Authenticated) and
            not security.authenticate(received)
        ):
            await self.send(sender, message.Denied(
                reason = "Authentication failed"
            ))
            return logging.warning(f"Message authentication failed: {received}")

        try:
            await self._on_receive(sender, received)
        except Exception as exception:
            logging.warning(f"Failed to handle message: {exception}")

    @staticmethod
    def _on_connect_fail(
        exception: Exception,
        host: host.Host,
        fails: int,
    ) -> None:
        """Callback for failed connect attempt"""
        logging.warning(f"Failed to connect to host {host}: {fails} time(s)")

    @staticmethod
    def _on_client_fail(uid: uuid.UUID) -> None:
        """Callback for client connection lost"""
        logging.warning(f"Lost connection to client: '{uid}'")

    def _on_server_fail(self, uid: uuid.UUID) -> None:
        """Callback for server connection lost"""
        logging.warning(f"Lost connection to server: '{uid}'")

        if len(self._servers) < self._majority:
            error.exit("Lost connection to the majority of servers")

    async def __aenter__(self) -> "Mediator":
        return self

    async def __aexit__(self, type, value, traceback) -> None:
        await self.close()

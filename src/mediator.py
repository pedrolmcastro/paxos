import uuid
import asyncio
import logging
import collections.abc

import host
import error
import paxos
import message
import security
import connection


class Mediator:
    def __init__(
        self,
        uid: uuid.UUID,
        hosts: collections.abc.Collection[host.Host]
    ) -> None:
        # Basic information
        self._uid = uid
        self._hosts = hosts
        self._majority = len(self._hosts) // 2 + 1

        # Server
        self._server: asyncio.Server | None = None

        # Connection maps
        self._clients = connection.Map()
        self._servers = connection.Map()
        self._clients.on_fail(self._on_client_fail)
        self._servers.on_fail(self._on_server_fail)

        # Paxos state
        self._promised: int | None = None
        self._previous: int | None = None
        self._accepted = ""

    async def start(self, port: host.Port, delays: connection.Delays) -> None:
        await self._clients.on_receive(self._on_receive)
        await self._servers.on_receive(self._on_receive)

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

    async def send(self, uid: uuid.UUID, message: message.Message) -> None:
        """Sends the message to the client or server with the uid"""

        if uid in self._servers:
            await self._servers.send(uid, message)
        else:
            await self._clients.send(uid, message)

    async def broadcast(self, message: message.Message) -> None:
        """Sends the message to all the connected servers"""
        await self._servers.broadcast(message)

    async def close(self):
        await self._clients.clear()
        await self._servers.clear()

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _handshake(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handshake performed between servers"""

        await message.send(writer, message.Server(self._uid.int))
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
                        uid = self._uid.int,
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

    async def _on_receive(
        self,
        uid: uuid.UUID,
        received: message.Message
    ) -> None:
        """Callback for received messages"""

        if (
            isinstance(received, security.Authenticated) and
            not security.authenticate(received)
        ):
            await self.send(uid, message.Denied(
                reason = "Authentication failed"
            ))
            return logging.warning(f"Message authentication failed: {received}")

        match received:
            case message.Accept():
                if self._promised is None or received.proposal > self._promised:
                    self._promised = received.proposal
                    self._previous = received.proposal
                    self._accepted = received.value

                    self.broadcast(message.Accepted(
                        value = self._accepted,
                        proposal = self._previous,
                    ))
                else:
                    self.send(uid, message.Denied(
                        reason = "Already promised to a higher proposal"
                    ))

            case message.Learned():
                # TODO: store
                pass

            case message.Prepare():
                if self._promised is None or received.proposal > self._promised:
                    self._promised = received.proposal

                    self.send(uid, message.Promise(
                        proposal = self._promised,
                        accepted = self._accepted,
                        previous = self._previous,
                    ))
                else:
                    self.send(uid, message.Denied(
                        reason = "Already promised to a higher proposal"
                    ))

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

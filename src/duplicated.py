#! /bin/python3.10

import uuid
import asyncio
import logging

from util import error

from network import host
from network import message
from network import connection

from app import cli


def on_connect_fail(exception: Exception, host: host.Host, fails: int) -> None:
    logging.error(f"Failed to connect to {host}: {fails} time(s)")

def on_fail() -> None:
    error.exit(f"Lost connection to the server")

def on_receive(sender: uuid.UUID, received: message.Message) -> None:
    logging.info(f"Received message: {received}")


async def main() -> None:
    logging.root.level = logging.INFO
    parsed = cli.Parser().duplicated.parse_args()

    async with connection.Map() as connections:
        async def handshake(
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter
        ):
            await message.send(writer, message.Client())
            received = await message.receive(reader)

            if not isinstance(received, message.Acknowledge):
                raise ValueError(f"Handskahe failed")

            uid = uuid.UUID(int = len(connections))

            await connections.set_reader(uid, reader, associated = writer)
            await connections.set_writer(uid, writer)

        await connections.on_receive(on_receive)
        connections.on_fail(on_fail)

        await connection.connectall(
            handshake = handshake,
            on_fail = on_connect_fail,
            delays = [0.1, 1.0, 2.0, 5.0],
            hosts = [parsed.first, parsed.second],
        )

        if len(connections) < 2:
            error.exit("Failed to connect to servers")

        await connections.send(uuid.UUID(int = 0), message.Write(value = "0"))
        await connections.send(uuid.UUID(int = 1), message.Write(value = "1"))

        await asyncio.sleep(1.5)


if __name__ == "__main__":
    asyncio.run(main())

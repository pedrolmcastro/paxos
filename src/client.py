#! /bin/python3.10

import asyncio
import logging
import aioconsole # type: ignore

from util import error

from network import host
from network import message
from network import connection

from app import cli


async def handshake(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    await message.send(writer, message.Client())
    received = await message.receive(reader)

    if not isinstance(received, message.Acknowledge):
        raise ValueError(f"Handskahe failed")

def on_connect_fail(exception: Exception, host: host.Host, fails: int) -> None:
    logging.error(f"Failed to connect to server: {fails} time(s)")

def on_fail() -> None:
    error.exit(f"Lost connection to the server")

def on_receive(received: message.Message) -> None:
    logging.info(f"Received message: {received}")


async def main() -> None:
    logging.root.level = logging.INFO
    parsed = cli.Parser().client.parse_args()

    async with connection.Connection() as connected:
        await connected.on_receive(on_receive)
        connected.on_fail(on_fail)

        try:
            reader, writer = await connection.connect(
                host = parsed.host,
                handshake = handshake,
                on_fail = on_connect_fail,
                delays = [0.1, 1.0, 2.0, 5.0],
            )
        except Exception:
            error.exit("Failed to connect to the server")

        await connected.set_reader(reader, associated = writer)
        await connected.set_writer(writer)

        while True:
            inputed = await aioconsole.ainput()

            if inputed == "quit":
                break

            if len(splited := inputed.split()) < 2:
                logging.error("Missing command parameter")
                continue

            command, parameter, *_ = splited

            match command:
                case "write":
                    await connected.send(message.Write(value = parameter))

                case "search":
                    await connected.send(message.Search(
                        value = parameter,
                        recurse = True
                    ))

                case _:
                    logging.error(f"Unknown command: {command}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Quit")

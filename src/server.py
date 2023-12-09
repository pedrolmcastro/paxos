import uuid
import asyncio
import logging
import pathlib
import dataclasses

from cli import Parser
from util import Error
from message import Message
from connection import Connection
from host import Host, Hostfile, Port
from security import Security, Authenticated


@dataclasses.dataclass(frozen = True)
class Info:
    port: Port
    secret: str
    majority: int
    uid: uuid.UUID
    hosts: list[Host]
    hostfile: pathlib.Path


def onreceive(message: Message.Any) -> None:
    if isinstance(message, Authenticated):
        print(f"Authenticated: {Security().authenticate(message)}")

    print(message)


async def main() -> None:
    logging.root.level = logging.DEBUG
    info = parse()

    address = info.hosts[0].addresses[0]
    reader, writer = await asyncio.open_connection(address.address, address.port.number)

    async with Connection() as connection:
        connection.reader = reader
        connection.writer = writer

        connection.onreceive(onreceive)

        message = Message.Accept("Hello, world", 1)
        await connection.send(message)

        await asyncio.sleep(0.5)


def parse() -> Info:
    parsed = Parser().server.parse_args()
    logging.debug(f"Selected port: {parsed.port}")
    logging.debug(f"Hostfile path: {parsed.hostfile}")

    try:
        hosts = Hostfile.parse(parsed.hostfile)
    except Exception as exception:
        Error.exit(str(exception))

    logging.debug(f"Hosts: [{', '.join(map(str, hosts))}]")

    uid = uuid.uuid4()
    logging.debug(f"Generated UID: {uid}")

    secret = Security().secret
    logging.debug(f"Detected secret: {'*' * len(secret)}")

    majority = len(hosts) // 2 + 1
    logging.debug(f"Calculated majority: {majority}")

    logging.info("Parsing phase done")

    return Info(
        uid = uid,
        hosts = hosts,
        secret = secret,
        port = parsed.port,
        majority = majority,
        hostfile = parsed.hostfile,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Server closed")

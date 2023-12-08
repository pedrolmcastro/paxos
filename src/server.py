import uuid
import typing
import asyncio
import logging
import pathlib
import dataclasses

from cli import Parser
from util import Error
from message import Message
from connections import Connections
from host import Host, Hostfile, Port


@dataclasses.dataclass(frozen = True)
class Info:
    port: Port
    majority: int
    uid: uuid.UUID
    hosts: list[Host]
    hostfile: pathlib.Path


async def main():
    logging.root.level = logging.DEBUG
    info = parse()

    # This must be defined early to be accessable from the closures
    connections: Connections | None = None

    async def on_disconnect(length: int):
        if length < info.majority:
            await typing.cast(Connections, connections).close()
            Error.exit("Lost connection to the majority of the servers")

    async def serve(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        pass

    # try:
    #     server = await asyncio.start_server(serve, "localhost", port)
    # except Exception as exception:
    #     error(f"Failed to start server: {exception}")

    connections = await Connections.connect(info.hosts, [1, 2, 5], on_disconnect)

    if len(connections) < info.majority:
        await connections.close()
        Error.exit("Failed to connect to the majority of the servers")

    # await server.serve_forever()

    message = Message.Accepted("Hello, world!", 0)
    await connections.broadcast(Message.encode(message))


def parse() -> Info:
    parsed = Parser().server.parse_args()
    logging.debug(f"Selected port: {parsed.port}")
    logging.debug(f"Hostfile path: {parsed.hostfile}")

    try:
        hosts = Hostfile.parse(parsed.hostfile)
    except Exception as exception:
        Error.exit(str(exception))

    logging.debug(f"Hosts: [{', '.join(map(str, hosts))}]")

    majority = len(hosts) // 2 + 1
    logging.debug(f"Calculated majority: {majority}")

    uid = uuid.uuid4()
    logging.debug(f"Generated UID: {uid}")

    logging.info("Parsing successfully concluded")

    return Info(parsed.port, majority, uid, hosts, parsed.hostfile)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server closed")

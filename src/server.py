import sys
import uuid
import typing
import asyncio
import logging

from cli import Parser
from util import Error
from message import Message
from connections import Connections
from host import Host, Hostfile, Port


async def main():
    logging.root.level = logging.DEBUG
    uid, port, hosts, majority = parse()


    # This must be defined early to be accessable from the closures
    connections: Connections | None = None

    async def on_disconnect(length: int):
        if length < majority:
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


    connections = await Connections.connect(hosts, [1, 2, 5], on_disconnect)

    if len(connections) < majority:
        await connections.close()
        Error.exit("Failed to connect to the majority of the servers")


    # await server.serve_forever()


    message = Message.Accepted("Hello, world!", 0)
    await connections.broadcast(Message.encode(message))


def parse() -> tuple[uuid.UUID, Port, list[Host], int]:
    # Parse CLI inputs
    parsed = Parser.server.parse_args(sys.argv[1:])

    logging.debug(f"Port: {parsed.port}")
    logging.debug(f"Hostfile: {parsed.hostfile}")


    # Parse hostfile
    try:
        hosts = Hostfile.parse(parsed.hostfile)
    except Exception as exception:
        Error.exit(str(exception))

    logging.debug(f"Hosts list: [{', '.join(map(str, hosts))}]")


    # Calculate the majority for the Paxos algorithm
    majority = len(hosts) // 2 + 1
    logging.debug(f"Majority: {majority}")


    # Generate the UID
    uid = uuid.uuid4()
    logging.debug(f"UID: {uid}")


    logging.info("Parsing successfully concluded")
    return uid, parsed.port, hosts, majority


if __name__ == "__main__":
    asyncio.run(main())

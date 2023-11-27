import sys
import uuid
import typing
import asyncio
import logging

from host import Host
from port import Port
from cli import Parser
from connections import Connections


async def main():
    logging.root.level = logging.DEBUG
    uid, port, hosts, majority = parse()


    # This must be defined early to be accessable from the closures
    connections: Connections | None = None

    async def on_disconnect(length: int):
        if length < majority:
            await typing.cast(Connections, connections).close()
            error("Lost connection to the majority of the servers")

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
        error("Failed to connect to the majority of the servers")


    # await server.serve_forever()


    for _ in range(5):
        await asyncio.sleep(5)
        await connections.broadcast(b"Hello, world!\n")


def parse() -> tuple[uuid.UUID, Port, list[Host], int]:
    # Parse CLI inputs
    parsed = Parser.server.parse_args(sys.argv[1:])

    logging.debug(f"Parsed port: {parsed.port}")
    logging.debug(f"Parsed hostfile: {parsed.hostfile}")


    # Parse hostfile
    try:
        hosts = Host.parse_hostfile(parsed.hostfile)
    except Exception as exception:
        Parser.server.error(str(exception))

    logging.debug(f"Parsed host list: [{', '.join(map(str, hosts))}]")


    # Calculate the majority for the Paxos algorithm
    majority = len(hosts) // 2 + 1
    logging.debug(f"Calculated majority: {majority}")


    # Generate the UID
    uid = uuid.uuid4()
    logging.debug(f"Generated UID: {uid}")


    logging.info("Parsing successfully concluded")
    return uid, parsed.port, hosts, majority


def error(message: str, code = 1) -> typing.NoReturn:
    logging.error(message)
    sys.exit(code)


if __name__ == "__main__":
    asyncio.run(main())

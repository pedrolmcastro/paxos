import sys
import asyncio
import logging
from typing import NoReturn
from uuid import UUID, uuid4

import cli
import connection
from port import Port
from message import Message
from host import Host, from_hostfile


async def main():
    logging.root.level = logging.DEBUG
    uuid, port, hosts, majority = parse()


    def ondisconnect(length: int) -> NoReturn:
        if length < majority:
            error("Lost connection to the majority of nodes")


    async with await connection.Manager.connect(hosts, [1, 2], ondisconnect) as connections:
        if len(connections) < majority:
            error("Failed to connect to the majority of nodes")

        while True:
            await asyncio.sleep(5)
            await connections.broadcast(Message(b"Hello, World!\n").payload)



def parse() -> tuple[UUID, Port, list[Host], int]:
    # Parse CLI inputs
    parser = cli.Parser.server
    parsed = parser.parse_args(sys.argv[1:])

    logging.debug(f"Parsed port: {parsed.port}")
    logging.debug(f"Parsed hostfile: {parsed.hostfile}")


    # Parse hostfile
    try:
        hosts = from_hostfile(parsed.hostfile)
    except Exception as exception:
        parser.error(str(exception))

    logging.debug(f"Parsed host list: [{', '.join(map(str, hosts))}]")


    # Calculate the majority for the Paxos algorithm
    majority = len(hosts) // 2 + 1
    logging.debug(f"Calculated majority: {majority}")


    # Generate the UUID
    uuid = uuid4()
    logging.debug(f"Generated UUID: {uuid}")


    logging.info("Parsing successfully concluded")
    return uuid, parsed.port, hosts, majority


def error(message: str, code = 1) -> NoReturn:
    logging.error(message)
    sys.exit(code)


if __name__ == "__main__":
    asyncio.run(main())

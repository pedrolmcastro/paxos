import sys
import asyncio
import logging
from uuid import UUID, uuid4

import cli
import connection
from port import Port
from host import Host, from_hostfile


async def main():
    logging.root.level = logging.DEBUG

    uuid, port, hosts, majority = parse()

    async with await connection.Manager.connect(hosts, [1, 2]) as connections:
        print(len(connections))


def parse() -> tuple[UUID, Port, list[Host], int]:
    # Parse CLI inputs
    parser = cli.Parser.server
    parsed = parser.parse_args(sys.argv[1:])

    logging.debug(f"Parsed hostfile: {parsed.hostfile}")
    logging.debug(f"Parsed port: {parsed.port}")


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


    logging.info("Concluded parsing phase")
    return uuid, parsed.port, hosts, majority


if __name__ == "__main__":
    asyncio.run(main())

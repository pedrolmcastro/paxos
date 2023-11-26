import sys
import logging
from uuid import UUID, uuid4

import cli
from port import Port
from host import Host, from_hostfile


def main():
    uuid, port, hosts, majority = parse()


def parse() -> (UUID, Port, list[Host], int):
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
    logging.root.level = logging.DEBUG
    main()

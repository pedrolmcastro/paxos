import sys

import cli
import host


def main():
    # Parse CLI inputs
    parser = cli.Parser.server
    parsed = parser.parse_args(sys.argv[1:])

    # Parse hostfile
    try:
        hosts = host.from_hostfile(parsed.hostfile)
    except Exception as exception:
        parser.error(str(exception))

    # Calculate the majority for the Paxos algorithm
    majority = len(hosts) // 2 + 1


    print(f"Port: {parsed.port}")
    print(f"Hostfile: {parsed.hostfile}")
    print(f"Hosts: {' '.join(map(str, hosts))}")
    print(f"Majority: {majority}")


if __name__ == "__main__":
    main()

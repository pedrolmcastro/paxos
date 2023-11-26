import sys

import cli
import host


def main():
    parser = cli.Parser.server
    parsed = parser.parse_args(sys.argv[1:])

    try:
        hosts = host.from_hostfile(parsed.hostfile)
    except Exception as exception:
        parser.error(str(exception))

    print(f"Port: {parsed.port}")
    print(f"Hostfile: {parsed.hostfile}")
    print(f"Hosts: {' '.join(map(str, hosts))}")


if __name__ == "__main__":
    main()

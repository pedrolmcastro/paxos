import sys

import cli


def main():
    parser = cli.Parser()
    parsed = parser.parse(sys.argv[1:])

    print(f"Port: {parsed.port}")
    print(f"Hosts: [{', '.join(str(host) for host in parsed.hosts)}]")


if __name__ == "__main__":
    main()

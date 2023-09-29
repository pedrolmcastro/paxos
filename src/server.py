import sys

import cli


def main():
    parsed = cli.Parser().parse(sys.argv[1:])

    print(f"Port: {parsed.port}")
    print(f"Hosts: [{', '.join(str(host) for host in parsed.hosts)}]")


if __name__ == "__main__":
    main()

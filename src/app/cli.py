import pathlib
import argparse

from util import singleton

from network import host


class Parser(metaclass = singleton.Singleton):
    """Singleton to hold the CLI parsers"""

    def __init__(self) -> None:
        # Server parser

        self.server = argparse.ArgumentParser(
            epilog = "HOST must be IPV4:PORT or [IPV6]:PORT or HOSTNAME:PORT",
        )

        self.server.add_argument(
            "-p",
            "--port",
            required = True,
            type = host.Port.from_str,
            help = "Port where this server will listen for TCP connections",
        )

        self.server.add_argument(
            "-f",
            "--hostfile",
            required = True,
            type = pathlib.Path,
            help = "Path to text file with a white space separeted HOST list",
        )

        # Client parser

        self.client = argparse.ArgumentParser()

        self.client.add_argument(
            "-H",
            "--host",
            required = True,
            type = host.Host.from_hostport,
            help = "Host in format IPV4:PORT or [IPV6]:PORT or HOSTNAME:PORT",
        )

        # Alternative client parser

        self.duplicated = argparse.ArgumentParser()

        self.duplicated.add_argument(
            "-f",
            "--first",
            required = True,
            type = host.Host.from_hostport,
            help = "Host in format IPV4:PORT or [IPV6]:PORT or HOSTNAME:PORT"
        )

        self.duplicated.add_argument(
            "-s",
            "--second",
            required = True,
            type = host.Host.from_hostport,
            help = "Host in format IPV4:PORT or [IPV6]:PORT or HOSTNAME:PORT"
        )

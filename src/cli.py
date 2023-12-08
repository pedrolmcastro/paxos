import pathlib
import argparse

from host import Port
from util import Singleton


class Parser(metaclass = Singleton):
    """Singleton to hold the CLI parsers"""

    def __init__(self) -> None:
        # Server parser

        self.server = argparse.ArgumentParser(
            epilog = "HOST must be IPv4:PORT or [IPv6]:PORT or HOSTNAME:PORT",
        )

        self.server.add_argument("-p", "--port",
            required = True,
            type = Port.from_str,
            help = "Port where this server will listen for TCP connections",
        )

        self.server.add_argument("-f", "--hostfile",
            required = True,
            type = pathlib.Path,
            help = "Path to text file with a white space separeted HOST list",
        )

        # TODO: Client parser

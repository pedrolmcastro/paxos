import typing
import argparse

import host


class Parser:
    def __init__(self) -> None:
        self._parser = argparse.ArgumentParser(
            epilog = "HOST must be IPv4:PORT or [IPv6]:PORT or HOSTNAME:PORT",
        )

        self._parser.add_argument("-p", "--port",
            required = True,
            type = host.Port.from_str,
            help = "Port where this server will listen for TCP connections",
        )

        group = self._parser.add_mutually_exclusive_group(required = True)

        group.add_argument("-l", "--hostlist",
            nargs = '+',
            dest = "hosts",
            metavar = "HOST",
            type = host.Host.from_hostport,
            help = "List of HOST locations of the other paxos servers",
        )

        group.add_argument("-f", "--hostfile",
            dest = "hosts",
            metavar = "HOSTFILE",
            type = host.from_hostfile,
            help = "Path to text file with a white space separeted HOST list",
        )


    def parse(self, args: typing.Sequence[str]) -> argparse.Namespace:
        return self._parser.parse_args(args)

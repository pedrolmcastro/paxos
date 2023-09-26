import typing
import argparse

import host


class Parser:
    def __init__(self) -> None:
        self._parser = argparse.ArgumentParser(
            usage = f"%(prog)s -p PORT (-l HOST:PORT [HOST:PORT ...] | -f HOSTFILE)"
        )

        self._parser.add_argument("-p", "--port",
            required = True,
            type = host.Port.from_str,
            help = "Port number where this server will listen for TCP connections",
        )

        group = self._parser.add_mutually_exclusive_group(required = True)

        group.add_argument("-l", "--hostlist",
            nargs = '+',
            dest = "hosts",
            type = host.Host.from_hostport,
            help = "List of HOST:PORT locations of the other paxos servers",
        )

        group.add_argument("-f", "--hostfile",
            dest = "hosts",
            type = host.from_hostfile,
            help = "Path to text file containing a HOST:PORT list separated by white spaces",
        )


    def parse(self, args: typing.Sequence[str]) -> argparse.Namespace:
        return self._parser.parse_args(args)

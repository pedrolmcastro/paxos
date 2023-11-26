import pathlib
import argparse

import port


class Parser:
    # Server parser
    server = argparse.ArgumentParser(
        epilog = "HOST must be IPv4:PORT or [IPv6]:PORT or HOSTNAME:PORT",
    )

    server.add_argument("-p", "--port",
        required = True,
        type = port.Port.from_str,
        help = "Port where this server will listen for TCP connections",
    )

    server.add_argument("-f", "--hostfile",
        required = True,
        type = pathlib.Path,
        help = "Path to text file with a white space separeted HOST list",
    )


    # Client parser
    client = argparse.ArgumentParser()

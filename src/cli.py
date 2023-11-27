import pathlib
import argparse

from port import Port


class Parser:
    """Namespace to hold the CLI parser objects"""
    

    # Server parser
    server = argparse.ArgumentParser(
        epilog = "HOST must be IPv4:PORT or [IPv6]:PORT or HOSTNAME:PORT",
    )

    server.add_argument("-p", "--port",
        required = True,
        type = Port.from_str,
        help = "Port where this server will listen for TCP connections",
    )

    server.add_argument("-f", "--hostfile",
        required = True,
        type = pathlib.Path,
        help = "Path to text file with a white space separeted HOST list",
    )


    # Client parser
    client = argparse.ArgumentParser()

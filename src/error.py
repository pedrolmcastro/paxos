import sys
import typing
import logging


def exit(message: str, code = 1) -> typing.NoReturn:
        logging.error(message)
        sys.exit(code)

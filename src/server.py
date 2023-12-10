import uuid
import asyncio
import logging
import pathlib

import cli
import host
import error
import storage
import mediator
import security


async def main() -> None:
    logging.root.level = logging.DEBUG

    parsed = cli.Parser().server.parse_args()
    logging.debug(f"Selected port: {parsed.port}")

    try:
        hosts = host.Host.from_hostfile(parsed.hostfile)
    except Exception as exception:
        error.exit(str(exception))

    logging.debug(f"Hosts: [{', '.join(map(str, hosts))}]")

    try:
        store = storage.Storage(pathlib.Path(f"storage/{parsed.port}.txt"))
    except Exception as exception:
        error.exit(f"Failed to open storage: {exception}")

    security.Context()

    uid = uuid.uuid4()
    logging.debug(f"Generated UID: {uid}")

    async with mediator.Mediator(uid, store, hosts) as server:
        await server.start(parsed.port, [0.1, 1.0, 2.0, 5.0])
        await server.done()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Server closed")

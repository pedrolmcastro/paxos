import uuid
import asyncio
import logging
import pathlib
import dataclasses

import cli
import host
import error
import message
import security
import connection


@dataclasses.dataclass(frozen = True)
class Data:
    secret: str
    majority: int
    uid: uuid.UUID
    port: host.Port
    hostfile: pathlib.Path
    hosts: list[host.Host]


def on_receive(uid: uuid.UUID, received: message.Message) -> None:
    print(f"Received from: '{uid}'")


async def main() -> None:
    logging.root.level = logging.DEBUG
    data = parse()

    async with connection.Map() as connections:
        connections.on_receive(on_receive)

        async def handshake(
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter
        ) -> None:
            uid = uuid.uuid4()
            print(f"Handshake with: '{uid}'")

            connections[uid] = connection.Connection()
            await connections[uid].set_reader(reader, associated = writer)
            await connections[uid].set_writer(writer)

        await connection.connectall(data.hosts, [0.1, 1, 2, 5], handshake)

        for _ in range(3):
            for uid in connections:
                await connections.send(uid, message.Denied(str(uid)))

            await asyncio.sleep(5)


def parse() -> Data:
    parsed = cli.Parser().server.parse_args()
    logging.debug(f"Selected port: {parsed.port}")
    logging.debug(f"Hostfile path: {parsed.hostfile}")

    try:
        hosts = host.Host.from_hostfile(parsed.hostfile)
    except Exception as exception:
        error.exit(str(exception))

    logging.debug(f"Hosts: [{', '.join(map(str, hosts))}]")

    uid = uuid.uuid4()
    logging.debug(f"Generated UID: {uid}")

    secret = security.Context().secret
    logging.debug(f"Detected secret: {'*' * len(secret)}")

    majority = len(hosts) // 2 + 1
    logging.debug(f"Calculated majority: {majority}")

    logging.info("Parsing phase done")

    return Data(
        uid = uid,
        hosts = hosts,
        secret = secret,
        port = parsed.port,
        majority = majority,
        hostfile = parsed.hostfile,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Server closed")

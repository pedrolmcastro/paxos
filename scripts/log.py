# Simple server that listens on the given port and prints the received messages

import sys
import asyncio


async def main():
    if len(sys.argv) < 2:
        error(f"Usage: python {sys.argv[0]} PORT")

    if not sys.argv[1].isdigit():
        error(f"Invalid port number: {sys.argv[1]}")

    port = int(sys.argv[1])

    if port <= 0 or port > 65535:
        error(f"Port number out of range: {port}")

    server = await asyncio.start_server(serve, host = "localhost", port = port)
    await server.serve_forever()


async def serve(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    while True:
        try:
            read = await reader.read(1024)
        except Exception:
            return

        if not read:
            return

        print(read)


def error(message: str, code = 1):
    print(f"[Error] {message}", file = sys.stderr)
    sys.exit(code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()

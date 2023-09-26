import socket
import pathlib
import dataclasses


@dataclasses.dataclass
class Port:
    number: int

    def __post_init__(self) -> None:
        if self.number <= 0 or self.number > 65535:
            raise ValueError(f"port number '{self.number}' isn't in range [1, 65535]")

    @classmethod
    def from_str(cls, number: str) -> "Port":
        if not number.isdigit():
            raise ValueError(f"port number '{number}' ins't a valid unsigned int")

        return cls(int(number))


    def __str__(self) -> str:
        return str(self.number)


@dataclasses.dataclass
class Host:
    Sockaddr = tuple[str, int] | tuple[str, int, int, int]
    Address = tuple[socket.AddressFamily, socket.SocketKind, int, str, Sockaddr]


    host: str
    port: Port
    info: list[Address] = dataclasses.field(init = False)

    def __post_init__(self) -> None:
        self.host = self.host.strip()

        try:
            self.info = socket.getaddrinfo(self.host, self.port.number, proto = socket.IPPROTO_TCP)
        except socket.gaierror:
            raise ValueError(f"failed to get address info for {self}")

    @classmethod
    def from_hostport(cls, hostport: str) -> "Host":
        if ':' not in hostport:
            raise ValueError(f"missing port number on {hostport}")

        host, port = hostport.split(':', 1)
        return cls(host, Port.from_str(port))


    @property
    def tuple(self) -> tuple[str, int]:
        return self.host, self.port.number


    def __str__(self) -> str:
        return f"{self.host}:{self.port}"


def from_hostfile(filepath: str | pathlib.Path) -> list[Host]:
    filepath = pathlib.Path(filepath)

    if not filepath.is_file():
        raise ValueError(f"{filepath} doesn't point to a valid text file")

    with filepath.open() as hostfile:
        return [Host.from_hostport(hostport) for hostport in hostfile.read().strip().split()]

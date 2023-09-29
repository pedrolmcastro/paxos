import re
import socket
import pathlib
import dataclasses


@dataclasses.dataclass(frozen = True)
class Port:
    number: int


    def __post_init__(self) -> None:
        if self.number <= 0 or self.number > 65535:
            raise ValueError(f"port out of range [1, 65535]: '{self.number}'")

    @classmethod
    def from_str(cls, number: str) -> "Port":
        if not number.isdigit():
            raise ValueError(f"invalid unsigned int: '{number}'")

        return cls(int(number))


    def __str__(self) -> str:
        return str(self.number)


@dataclasses.dataclass(frozen = True)
class Address:
    """Object-like representation of the tuple returned by socket.getaddrinfo"""


    Sockaddr = tuple[str, int] | tuple[str, int, int, int]
    Data = tuple[socket.AddressFamily, socket.SocketKind, int, str, Sockaddr]

    data: Data


    @property
    def family(self) -> socket.AddressFamily:
        return self.data[0]

    @property
    def type(self) -> socket.SocketKind:
        return self.data[1]

    @property
    def proto(self) -> int:
        return self.data[2]

    @property
    def canonname(self) -> str:
        return self.data[3]

    @property
    def sockaddr(self) -> Sockaddr:
        return self.data[4]

    @property
    def address(self) -> str:
        return self.sockaddr[0]

    @property
    def port(self) -> Port:
        return Port(self.sockaddr[1])


class Regex:
    """Regex to match IPv4:PORT or [IPv6]:PORT or HOSTNAME:PORT"""


    PORT = "\d+"

    IPV4 = "(?:\d{1,3}\.){3}\d{1,3}"
    IPV6 = "\[[:a-fA-F0-9]+\]" # Incorrect oversimplification
    HOSTNAME = "[-a-zA-Z0-9.]+"

    PATTERN = re.compile(f"({IPV4}|{IPV6}|{HOSTNAME}):({PORT})")


    @classmethod
    def match(cls, hostport: str) -> re.Match[str] | None:
        return cls.PATTERN.match(hostport)


@dataclasses.dataclass(frozen = True)
class Host:
    host: str
    port: Port
    info: list[Address] = dataclasses.field(init = False)


    def __post_init__(self) -> None:
        try:
            info = socket.getaddrinfo(
                self.host,
                self.port.number,
                proto = socket.IPPROTO_TCP
            )
        except socket.gaierror:
            raise ValueError(f"failed to get address info for '{self}'")

        object.__setattr__(self, "info", [Address(address) for address in info])

    @classmethod
    def from_hostport(cls, hostport: str) -> "Host":
        matched = Regex.match(hostport)

        if matched is None:
            raise ValueError(f"invalid hostport: '{hostport}'")

        host, port = matched.group(1, 2)

        if host.startswith('['):
            host = host[1:-1]

        return cls(host, Port.from_str(port))


    def __str__(self) -> str:
        return f"{self.host}:{self.port}"


def from_hostfile(filepath: str | pathlib.Path) -> list[Host]:
    filepath = pathlib.Path(filepath)

    if not filepath.is_file():
        raise ValueError(f"invalid text file: '{filepath}'")

    with filepath.open() as hostfile:
        hostports = hostfile.read().strip().split()

    return [Host.from_hostport(hostport) for hostport in hostports]

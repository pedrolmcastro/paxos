import re
import socket
import pathlib
import dataclasses


class Port:
    """Wrapper to represent a port with a valid number"""

    LOW = 1
    HIGH = 65535

    def __init__(self, number: int) -> None:
        if number < self.LOW or number > self.HIGH:
            raise ValueError(
                f"Port out of range [{self.LOW}, {self.HIGH}]: '{number}'"
            )

        self._number = number

    @classmethod
    def from_str(cls, number: str) -> "Port":
        if not number.isdigit():
            raise ValueError(f"Invalid unsigned int: '{number}'")

        return cls(int(number))

    @property
    def number(self):
        return self._number

    def __str__(self) -> str:
        return str(self._number)


@dataclasses.dataclass(frozen = True)
class Address:
    """Object-like representation of the tuple returned by socket.getaddrinfo"""

    Sockaddr = tuple[str, int] | tuple[str, int, int, int]

    data: tuple[socket.AddressFamily, socket.SocketKind, int, str, Sockaddr]

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


class _Regex:
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
    """Wrapper to represent a host with valid addressess"""

    host: str
    port: Port
    addresses: list[Address] = dataclasses.field(init = False)

    def __post_init__(self) -> None:
        try:
            addresses = socket.getaddrinfo(
                self.host,
                self.port.number,
                proto = socket.IPPROTO_TCP
            )
        except socket.gaierror:
            raise ValueError(f"Failed to get address information: '{self}'")

        object.__setattr__(
            self,
            "addresses",
            [Address(address) for address in addresses]
        )

    @classmethod
    def from_hostport(cls, hostport: str) -> "Host":
        matched = _Regex.match(hostport)

        if matched is None:
            raise ValueError(f"Invalid hostport: '{hostport}'")

        host, port = matched.group(1, 2)

        if host.startswith('['):
            host = host[1:-1]

        return cls(host, Port.from_str(port))

    @classmethod
    def from_hostfile(cls, filepath: pathlib.Path) -> list["Host"]:
        if not filepath.is_file():
            raise ValueError(f"Invalid text file: '{filepath}'")

        with filepath.open() as hostfile:
            hostports = hostfile.read().strip().split()

        return [cls.from_hostport(hostport) for hostport in hostports]

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"

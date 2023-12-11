import enum
import json
import struct
import typing
import asyncio
import dataclasses

from app import security


@dataclasses.dataclass(frozen = True)
class _Base:
    def __str__(self) -> str:
        items = dataclasses.asdict(self).items()
        values = (str(value) for field, value in items if field != "hash")
        return f"{self.__class__.__name__}({', '.join(values)})"


@dataclasses.dataclass(frozen = True)
class Accept(_Base, security.Authenticated):
    value: str
    proposal: int

@dataclasses.dataclass(frozen = True)
class Accepted(_Base, security.Authenticated):
    value: str
    proposal: int

@dataclasses.dataclass(frozen = True)
class Acknowledge(_Base):
    pass

@dataclasses.dataclass(frozen = True)
class Client(_Base):
    pass

@dataclasses.dataclass(frozen = True)
class Denied(_Base):
    reason: str

@dataclasses.dataclass(frozen = True)
class Found(_Base, security.Authenticated):
    value: str
    found: bool

@dataclasses.dataclass(frozen = True)
class Learn(_Base):
    value: str

@dataclasses.dataclass(frozen = True)
class Prepare(_Base, security.Authenticated):
    proposal: int

@dataclasses.dataclass(frozen = True)
class Promise(_Base, security.Authenticated):
    proposal: int
    accepted: str
    previous: int | None

@dataclasses.dataclass(frozen = True)
class Search(_Base):
    value: str
    recurse: bool

@dataclasses.dataclass(frozen = True)
class Server(_Base, security.Authenticated):
    uid: int

@dataclasses.dataclass(frozen = True)
class Write(_Base):
    value: str

@dataclasses.dataclass(frozen = True)
class Wrote(_Base):
    value: str


Message = (
    Accept | Accepted | Acknowledge | Client | Denied | Found | Learn |
    Prepare | Promise | Search | Server | Write | Wrote
)


class Type(enum.Enum):
    ACCEPT      = enum.auto()
    ACCEPTED    = enum.auto()
    ACKNOWLEDGE = enum.auto()
    CLIENT      = enum.auto()
    DENIED      = enum.auto()
    FOUND       = enum.auto()
    LEARN       = enum.auto()
    PREPARE     = enum.auto()
    PROMISE     = enum.auto()
    SEARCH      = enum.auto()
    SERVER      = enum.auto()
    WRITE       = enum.auto()
    WROTE       = enum.auto()

    @classmethod
    def from_message(cls, message: Message) -> "Type":
        match message:
            case Accept():
                return cls.ACCEPT
            case Accepted():
                return cls.ACCEPTED
            case Acknowledge():
                return cls.ACKNOWLEDGE
            case Client():
                return cls.CLIENT
            case Denied():
                return cls.DENIED
            case Found():
                return cls.FOUND
            case Learn():
                return cls.LEARN
            case Prepare():
                return cls.PREPARE
            case Promise():
                return cls.PROMISE
            case Search():
                return cls.SEARCH
            case Server():
                return cls.SERVER
            case Write():
                return cls.WRITE
            case Wrote():
                return cls.WROTE

    def to_type(self) -> type[Message]:
        match self:
            case self.ACCEPT:
                return Accept
            case self.ACCEPTED:
                return Accepted
            case self.ACKNOWLEDGE:
                return Acknowledge
            case self.CLIENT:
                return Client
            case self.DENIED:
                return Denied
            case self.FOUND:
                return Found
            case self.LEARN:
                return Learn
            case self.PREPARE:
                return Prepare
            case self.PROMISE:
                return Promise
            case self.SEARCH:
                return Search
            case self.SERVER:
                return Server
            case self.WRITE:
                return Write
            case self.WROTE:
                return Wrote

        raise ValueError(f"Unknown message type: '{self}'")


@dataclasses.dataclass(frozen = True)
class Header:
    type: Type
    length: int

    SIZE: typing.ClassVar[int] = 5
    _PACK: typing.ClassVar[str] = "!IB"

    def encode(self) -> bytes:
        return struct.pack(self._PACK, self.length, self.type.value)

    @classmethod
    def decode(cls, encoded: bytes) -> "Header":
        if len(encoded) != cls.SIZE:
            raise ValueError("Invalid encoded message header length")

        length, type = struct.unpack(cls._PACK, encoded)
        return cls(length = length, type = Type(type))


def encode(message: Message) -> bytes:
    payload = json.dumps(dataclasses.asdict(message)).encode()
    header = Header(length = len(payload), type = Type.from_message(message))
    return header.encode() + payload

def decode(header: Header, payload: bytes) -> Message:
    if len(payload) != header.length:
        raise ValueError("Invalid encoded message length")

    type = header.type.to_type()
    decoded = json.loads(payload)

    return type(**typing.cast(dict[str, typing.Any], decoded))


async def send(writer: asyncio.StreamWriter, message: Message) -> None:
    writer.write(encode(message))
    await writer.drain()

async def receive(reader: asyncio.StreamReader) -> Message:
    initial = await reader.readexactly(Header.SIZE)
    header = Header.decode(initial)

    payload = await reader.readexactly(header.length)
    return decode(header, payload)

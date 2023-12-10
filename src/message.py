import enum
import json
import struct
import typing
import asyncio
import dataclasses

import security


@dataclasses.dataclass(frozen = True)
class Accept(security.Authenticated):
    value: str
    proposal: int

@dataclasses.dataclass(frozen = True)
class Accepted(security.Authenticated):
    value: str
    proposal: int

@dataclasses.dataclass(frozen = True)
class Acknowledge:
    pass

@dataclasses.dataclass(frozen = True)
class Client:
    pass

@dataclasses.dataclass(frozen = True)
class Denied:
    reason: str

@dataclasses.dataclass(frozen = True)
class Found(security.Authenticated):
    value: str
    found: bool

@dataclasses.dataclass(frozen = True)
class Learned:
    value: str

@dataclasses.dataclass(frozen = True)
class Prepare(security.Authenticated):
    proposal: int

@dataclasses.dataclass(frozen = True)
class Promise(security.Authenticated):
    proposal: int
    accepted: str
    previous: int | None

@dataclasses.dataclass(frozen = True)
class Search:
    value: str
    recursive: bool

@dataclasses.dataclass(frozen = True)
class Server(security.Authenticated):
    uid: int

@dataclasses.dataclass(frozen = True)
class Write:
    value: str


Message = (
    Accept | Accepted | Acknowledge | Client | Denied | Found | Learned |
    Prepare | Promise | Search | Server | Write
)


class Type(enum.Enum):
    ACCEPT      = enum.auto()
    ACCEPTED    = enum.auto()
    ACKNOWLEDGE = enum.auto()
    CLIENT      = enum.auto()
    DENIED      = enum.auto()
    FOUND       = enum.auto()
    LEARNED     = enum.auto()
    PREPARE     = enum.auto()
    PROMISE     = enum.auto()
    SEARCH      = enum.auto()
    SERVER      = enum.auto()
    WRITE       = enum.auto()

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
            case Learned():
                return cls.LEARNED
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
            case self.LEARNED:
                return Learned
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

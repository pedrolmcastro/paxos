import enum
import json
import struct
import typing
import dataclasses

from security import Authenticated


class Message:
    """Namespace for functionalities related to network messages"""

    @dataclasses.dataclass(frozen = True)
    class Acknowledge:
        pass

    @dataclasses.dataclass(frozen = True)
    class Denied:
        reason: str

    @dataclasses.dataclass(frozen = True)
    class Write:
        value: str

    @dataclasses.dataclass(frozen = True)
    class Search:
        value: str
        recursive: bool

    @dataclasses.dataclass(frozen = True)
    class Found(Authenticated):
        value: str
        found: bool

    @dataclasses.dataclass(frozen = True)
    class Prepare(Authenticated):
        proposal: int

    @dataclasses.dataclass(frozen = True)
    class Promise(Authenticated):
        proposal: int
        accepted: str
        previous: int | None

    @dataclasses.dataclass(frozen = True)
    class Accept(Authenticated):
        value: str
        proposal: int

    @dataclasses.dataclass(frozen = True)
    class Accepted(Authenticated):
        value: str
        proposal: int


    Any = (
        Acknowledge | Denied | Write | Search | Found |
        Prepare | Promise | Accept | Accepted
    )


    class Type(enum.Enum):
        ACKNOWLEDGE = enum.auto()
        DENIED      = enum.auto()
        WRITE       = enum.auto()
        SEARCH      = enum.auto()
        FOUND       = enum.auto()
        PREPARE     = enum.auto()
        PROMISE     = enum.auto()
        ACCEPT      = enum.auto()
        ACCEPTED    = enum.auto()

        @classmethod
        def from_type(cls, type: type["Message.Any"]) -> "Message.Type":
            match type:
                case Message.Acknowledge:
                    return cls.ACKNOWLEDGE
                case Message.Denied:
                    return cls.DENIED
                case Message.Write:
                    return cls.WRITE
                case Message.Search:
                    return cls.SEARCH
                case Message.Found:
                    return cls.FOUND
                case Message.Prepare:
                    return cls.PREPARE
                case Message.Promise:
                    return cls.PROMISE
                case Message.Accept:
                    return cls.ACCEPT
                case Message.Accepted:
                    return cls.ACCEPTED

            raise ValueError(f"Unknown message type: '{type}'")

        def to_type(self) -> type["Message.Any"]:
            match self:
                case self.ACKNOWLEDGE:
                    return Message.Acknowledge
                case self.DENIED:
                    return Message.Denied
                case self.WRITE:
                    return Message.Write
                case self.SEARCH:
                    return Message.Search
                case self.FOUND:
                    return Message.Found
                case self.PREPARE:
                    return Message.Prepare
                case self.PROMISE:
                    return Message.Promise
                case self.ACCEPT:
                    return Message.Accept
                case self.ACCEPTED:
                    return Message.Accepted

            raise ValueError(f"Unknown message type: '{self}'")


    @dataclasses.dataclass(frozen = True)
    class Header:
        length: int
        type: "Message.Type"

        SIZE: typing.ClassVar[int] = 5
        _PACK: typing.ClassVar[str] = "!IB"

        def encode(self) -> bytes:
            return struct.pack(self._PACK, self.length, self.type.value)

        @classmethod
        def decode(cls, encoded: bytes) -> "Message.Header":
            if len(encoded) != cls.SIZE:
                raise ValueError("Invalid encoded message header length")

            length, type = struct.unpack(cls._PACK, encoded)
            return cls(length = length, type = Message.Type(type))


    @classmethod
    def encode(cls, message: Any) -> bytes:
        payload = json.dumps(dataclasses.asdict(message)).encode()

        header = cls.Header(
            length = len(payload),
            type = cls.Type.from_type(type(message)),
        )

        return header.encode() + payload

    @classmethod
    def decode(cls, header: Header, payload: bytes) -> Any:
        if len(payload) != header.length:
            raise ValueError("Invalid encoded message length")

        type = header.type.to_type()
        decoded = json.loads(payload)

        return type(**typing.cast(dict[str, typing.Any], decoded))

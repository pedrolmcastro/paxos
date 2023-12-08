import enum
import json
import struct
import typing
import dataclasses

from security import Authn


class Message:
    """Namespace for functionality related to network messages"""


    @dataclasses.dataclass(frozen = True)
    class Ack:
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
    class Found(Authn):
        value: str
        found: bool

    @dataclasses.dataclass(frozen = True)
    class Prepare(Authn):
        proposal: int

    @dataclasses.dataclass(frozen = True)
    class Promise(Authn):
        proposal: int
        accepted: str
        previous: int | None

    @dataclasses.dataclass(frozen = True)
    class Accept(Authn):
        value: str
        proposal: int

    @dataclasses.dataclass(frozen = True)
    class Accepted(Authn):
        value: str
        proposal: int


    Any = (
        Ack | Denied | Write | Search | Found |
        Prepare | Promise | Accept | Accepted
    )


    class _Type(enum.Enum):
        ACK      = enum.auto()
        DENIED   = enum.auto()
        WRITE    = enum.auto()
        SEARCH   = enum.auto()
        FOUND    = enum.auto()
        PREPARE  = enum.auto()
        PROMISE  = enum.auto()
        ACCEPT   = enum.auto()
        ACCEPTED = enum.auto()


        @classmethod
        def from_type(cls, type: type["Message.Any"]) -> "Message._Type":
            match type:
                case Message.Ack:
                    return cls.ACK
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
                case self.ACK:
                    return Message.Ack
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


    @classmethod
    def encode(cls, message: "Message.Any") -> bytes:
        payload = json.dumps(dataclasses.asdict(message)).encode()
        enumerated = cls._Type.from_type(type(message))
        return struct.pack("!IB", len(payload), enumerated.value) + payload

    @classmethod
    def decode(cls, encoded: bytes) -> "Message.Any":
        if len(encoded) < 5:
            raise ValueError("Missing encoded message header")

        length, enumerated = struct.unpack("!IB", encoded[:5])

        if len(encoded) != length + 5:
            raise ValueError("Invalid encoded message length")

        type = cls._Type(enumerated).to_type()
        payload = typing.cast(dict[str, typing.Any], json.loads(encoded[5:]))

        return type(**payload)

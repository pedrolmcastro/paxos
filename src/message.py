import struct
import dataclasses


@dataclasses.dataclass(frozen = True)
class Message:
    payload: bytes


    def to_bytes(self) -> bytes:
        return struct.pack(">I", len(self.payload)) + self.payload

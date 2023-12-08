import os
import typing
import hashlib
import dataclasses

from util import Error, Singleton


@dataclasses.dataclass(frozen = True, kw_only = True)
class Authn:
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            object.__setattr__(self, "hash", Security().hash(self))


class Security(metaclass = Singleton):
    """Singleton class to manage security functionalities"""

    def __init__(self) -> None:
        self._VARIABLE = "SECRET"
        secret = os.getenv(self._VARIABLE)

        if secret is None:
            Error.exit(f"Missing environment variable: '{self._VARIABLE}'")

        self._secret = secret

    @property
    def secret(self) -> str:
        return self._secret

    def _encode(self, value: typing.Any) -> bytes:
        match value:
            case None:
                return b""
            case int():
                return value.to_bytes(8, "big")
            case str():
                return value.encode()
            case bytes():
                return value

        raise ValueError(f"Unable to encode type: '{type(value)}'")

    def hash(self, authn: Authn) -> str:
        items = dataclasses.asdict(authn).items()
        values = (value for field, value in items if field != "hash")

        hash = hashlib.sha256(
            self._encode(self.secret) +
            b"".join(self._encode(value) for value in values)
        )

        return hash.hexdigest()

    def is_valid(self, authn: Authn) -> bool:
        return self.hash(authn) == authn.hash

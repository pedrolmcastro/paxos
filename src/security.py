import os
import typing
import hashlib
import dataclasses

import error
import singleton


class Context(metaclass = singleton.Singleton):
    """Singleton class to manage the security context"""

    def __init__(self) -> None:
        self._VARIABLE = "SECRET"
        secret = os.getenv(self._VARIABLE)

        if secret is None:
            error.exit(f"Missing environment variable: '{self._VARIABLE}'")

        self._secret = secret

    @property
    def secret(self) -> str:
        return self._secret


@dataclasses.dataclass(frozen = True, kw_only = True)
class Authenticated:
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            object.__setattr__(self, "hash", hash(self))


def _encode(value: typing.Any) -> bytes:
    match value:
        case None:
            return b""
        case int():
            return value.to_bytes(16, "big")
        case str():
            return value.encode()
        case bytes():
            return value

    raise ValueError(f"Unable to encode type: '{type(value)}'")

def hash(authenticated: Authenticated) -> str:
    items = dataclasses.asdict(authenticated).items()
    values = (value for field, value in items if field != "hash")

    hash = hashlib.sha256(
        _encode(Context().secret) +
        b"".join(_encode(value) for value in values)
    )

    return hash.hexdigest()

def authenticate(authenticated: Authenticated) -> bool:
    return hash(authenticated) == authenticated.hash

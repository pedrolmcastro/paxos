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

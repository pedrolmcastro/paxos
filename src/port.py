class Port:
    """Wrapper to represent a port with a valid number"""


    MIN = 1
    MAX = 65535


    def __init__(self, number: int) -> None:
        if number < self.MIN or number > self.MAX:
            raise ValueError(
                f"Port out of range [{self.MIN}, {self.MAX}]: '{number}'"
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

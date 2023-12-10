import pathlib
import collections.abc


class Storage:
    def __init__(self, filepath: pathlib.Path) -> None:
        self._filepath = filepath
        self._values: set[str] = set()

        with self._filepath.open() as file:
            for line in file:
                self._values.add(line)

    def write(self, value: str) -> None:
        if value not in self:
            return

        with self._filepath.open("a") as file:
            file.write(f"value\n")

        self._values.add(value)

    def __contains__(self, value: str) -> bool:
        return value in self._values

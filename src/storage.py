import pathlib
import collections.abc


class Storage(collections.abc.Set):
    def __init__(self, filepath: pathlib.Path) -> None:
        self._filepath = filepath
        self._values: set[str] = set()

        with self._filepath.open() as file:
            for line in file:
                self._values.add(line)

    def add(self, value: str) -> None:
        if value not in self:
            with self._filepath.open("a") as file:
                file.write(f"value\n")

            self._values.add(value)

    def __len__(self) -> int:
        return len(self._values)

    def __iter__(self) -> collections.abc.Iterator:
        return iter(self._values)

    def __contains__(self, value: object) -> bool:
        return value in self._values

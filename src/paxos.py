import dataclasses


@dataclasses.dataclass(frozen = True)
class Accepted:
    value: str
    proposal: int | None


class Paxos:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._promised: int | None = None
        self._accepted = Accepted("", None)

    def prepare(self, proposal: int) -> bool:
        if self._promised is None or proposal > self._promised:
            self._promised = proposal
            return True
        else:
            return False

    def accept(self, value: str, proposal: int) -> bool:
        if self._promised is None or proposal > self._promised:
            self._accepted = Accepted(value, proposal)
            self._promised = proposal
            return True
        else:
            return False

    @property
    def promised(self) -> int | None:
        return self._promised

    @property
    def accepted(self) -> Accepted:
        return self._accepted

import time
import uuid
import random
import asyncio
import collections
import dataclasses

from network import message
from network import mediator

from app import storage
from app import security


@dataclasses.dataclass
class _Accepted:
    value: str
    proposal: int

@dataclasses.dataclass
class _Accepting:
    value: str
    accepts: int

@dataclasses.dataclass
class _Proposing:
    value: str
    proposal: int
    promises: int
    maximum: int | None

@dataclasses.dataclass
class _Searching:
    fails: int
    searchers: list[uuid.UUID]

@dataclasses.dataclass
class _Writing:
    value: str
    writer: uuid.UUID


class Handler:
    def __init__(
        self,
        storage: storage.Storage,
        mediator: mediator.Mediator,
        delays: tuple[float, float],
    ) -> None:
        # Configuration
        self._delays = delays
        self._storage = storage
        self._mediator = mediator

        # State
        self._promised: int | None = None
        self._accepted: _Accepted | None = None
        self._proposing: _Proposing | None = None
        self._accepting: dict[int, _Accepting] = {}
        self._searching: dict[str, _Searching] = {}
        self._writing: collections.deque[_Writing] = collections.deque()

        # Tasks
        self._proposer: asyncio.Task[None] | None = None

    async def handle(
        self,
        sender: uuid.UUID,
        received: message.Message
    ) -> None:
        """Dispatches the message to the appropriate handler"""

        match received:
            case message.Accept():
                await self._on_accept(sender, received.value, received.proposal)
            case message.Accepted():
                await self._on_accepted(received.value, received.proposal)
            case message.Found():
                await self._on_found(received.value, received.found)
            case message.Learn():
                await self._on_learn(received.value)
            case message.Prepare():
                await self._on_prepare(sender, received.proposal)
            case message.Promise():
                await self._on_promise(
                    received.proposal,
                    received.accepted,
                    received.previous
                )
            case message.Search():
                await self._on_search(sender, received.value, received.recurse)
            case message.Write():
                await self._on_write(sender, received.value)
            case message.Acknowledge() | message.Denied():
                pass
            case _:
                raise ValueError(f"Unexpected message type: {type(received)}")

    async def _on_accept(
        self,
        sender: uuid.UUID,
        value: str,
        proposal: int
    ) -> None:
        """Handles an 'Accept' message"""

        if self._promised is None or proposal >= self._promised:
            self._promised = proposal
            self._accepted = _Accepted(value = value, proposal = proposal)

            await self._mediator.broadcast(message.Accepted(
                value = value,
                proposal = proposal,
            ))
        else:
            await self._mediator.send(sender, message.Denied(
                reason = "Already promised to a higher proposal"
            ))

    async def _on_accepted(self, value: str, proposal: int) -> None:
        """Handles an 'Accepted' message"""

        if proposal not in self._accepting:
            self._accepting[proposal] = _Accepting(value, 0)

        if value != self._accepting[proposal].value:
            del self._accepting[proposal]
            raise ValueError(f"Duplicate proposal number: {proposal}")

        self._accepting[proposal].accepts += 1

        if self._accepting[proposal].accepts >= self._mediator.majority:
            del self._accepting[proposal]
            await self._mediator.broadcast(message.Learn(value = value))

    async def _on_found(self, value: str, found: bool) -> None:
        """Handles a 'Found' message"""

        if value not in self._searching:
            return

        searchers = self._searching[value].searchers

        if found:
            del self._searching[value]
            response = message.Found(value = value, found = True)

            for searcher in searchers:
                await self._mediator.send(searcher, response)

            return

        self._searching[value].fails += 1

        if self._searching[value].fails >= self._mediator.majority:
            del self._searching[value]
            response = message.Found(value = value, found = False)

            for searcher in searchers:
                await self._mediator.send(searcher, response)

    async def _on_learn(self, value: str) -> None:
        """Handles a 'Learn' message"""

        self._storage.add(value)

        while self._writing and self._writing[0].value in self._storage:
            dequeued = self._writing.popleft()

            await self._mediator.send(dequeued.writer, message.Wrote(
                value = dequeued.value
            ))

        self._reset()

    async def _on_prepare(self, sender: uuid.UUID, proposal: int) -> None:
        """Handles a 'Prepare' message"""

        if self._promised is None or proposal > self._promised:
            self._promised = proposal

            if self._accepted is None:
                accepted = ""
                previous = None
            else:
                accepted = self._accepted.value
                previous = self._accepted.proposal

            await self._mediator.send(sender, message.Promise(
                proposal = self._promised,
                accepted = accepted,
                previous = previous,
            ))
        else:
            await self._mediator.send(sender, message.Denied(
                reason = "Already promised to a higher proposal"
            ))

    async def _on_promise(
        self,
        proposal: int,
        accepted: str,
        previous: int | None
    ) -> None:
        """Handles a 'Promise' message"""

        if self._proposing is None or proposal != self._proposing.proposal:
            return

        if previous is not None and(
            self._proposing.maximum is None or
            previous > self._proposing.maximum
        ):
            self._proposing.value = accepted

        self._proposing.promises += 1

        if self._proposing.promises >= self._mediator.majority:
            value = self._proposing.value
            self._proposing = None

            # Stop proposing for this round
            if self._proposer is not None:
                self._proposer.cancel()
                self._proposer = None

            await self._mediator.broadcast(message.Accept(
                value = value,
                proposal = proposal,
            ))

    async def _on_search(
        self,
        sender: uuid.UUID,
        value: str,
        recurse: bool,
    ) -> None:
        """Handles a 'Search' message"""

        if recurse:
            if value not in self._searching:
                self._searching[value] = _Searching(fails = 0, searchers = [])

            self._searching[value].searchers.append(sender)
            started = len(self._searching[value].searchers) == 1

            await self._mediator.send(sender, message.Acknowledge())

            if started:
                await self._mediator.broadcast(message.Search(
                    value = value,
                    recurse = False,
                ))
        else:
            await self._mediator.send(sender, message.Found(
                value = value,
                found = value in self._storage,
            ))

    async def _on_write(self, sender: uuid.UUID, value: str) -> None:
        """Handles a 'Write' message"""

        await self._mediator.send(sender, message.Acknowledge())
        self._writing.append(_Writing(value = value, writer = sender))

        # Start the task to propose the value
        if self._proposer is None:
            value = self._writing[0].value
            self._proposer = asyncio.create_task(self._propose(value))

    @staticmethod
    def _proposal() -> int:
        """Returns a new proposal number"""

        now = int(time.time() * 1000).to_bytes(8, byteorder = "big")
        uid = security.Context().uid.bytes[:8]

        return int.from_bytes(now + uid, byteorder = "big")

    async def _propose(self, value: str) -> None:
        """Repeatedly sends 'Prepare' messages until canceled"""

        while True:
            self._proposing = _Proposing(
                promises = 0,
                value = value,
                maximum = None,
                proposal = self._proposal()
            )

            await self._mediator.broadcast(message.Prepare(
                proposal = self._proposing.proposal
            ))

            delay = random.uniform(self._delays[0], self._delays[1])
            await asyncio.sleep(delay)

    def _reset(self) -> None:
        """Resets the internal state to go to the next round"""

        self._promised = None
        self._accepted = None
        self._proposing = None
        self._accepting.clear()

        if self._proposer is not None:
            self._proposer.cancel()
            self._proposer = None

        if self._writing:
            value = self._writing[0].value
            self._proposer = asyncio.create_task(self._propose(value))

import uuid
import dataclasses

import message
import storage
import mediator


@dataclasses.dataclass
class _Accepted:
    value: str
    proposal: int | None

@dataclasses.dataclass
class _Accepting:
    value: str
    received: int

@dataclasses.dataclass
class _Searching:
    fails: int
    searchers: list[uuid.UUID]


class Handler:
    def __init__(
        self,
        majority: int,
        storage: storage.Storage,
        mediator: mediator.Mediator,
    ) -> None:
        # Dependencies
        self._storage = storage
        self._mediator = mediator

        # Internal state
        self._majority = majority
        self._promised: int | None = None
        self._accepting: dict[int, _Accepting] = {}
        self._searching: dict[str, _Searching] = {}
        self._accepted = _Accepted(value = "", proposal = None)

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
            case message.Acknowledge():
                pass
            case message.Found():
                await self._on_found(received.value, received.found)
            case message.Learn():
                self._on_learn(received.value)
            case message.Prepare():
                await self._on_prepare(sender, received.proposal)
            case message.Search():
                await self._on_search(sender, received.value, received.recursive)

    async def _on_accept(
        self,
        sender: uuid.UUID,
        value: str,
        proposal: int
    ) -> None:
        """Handles an 'Accept' message"""

        if self._promised is None or proposal > self._promised:
            self._promised = proposal
            self._accepted.value = value
            self._accepted.proposal = proposal

            await self._mediator.broadcast(message.Accepted(
                value = self._accepted.value,
                proposal = self._accepted.proposal,
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
            raise ValueError("Received different values with same proposal")

        self._accepting[proposal].received += 1

        if self._accepting[proposal].received >= self._majority:
            await self._mediator.broadcast(message.Learn(value = value))
            del self._accepting[proposal]

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
        else:
            self._searching[value].fails += 1

        if self._searching[value].fails >= self._majority:
            del self._searching[value]
            response = message.Found(value = value, found = False)

            for searcher in searchers:
                await self._mediator.send(searcher, response)

    def _on_learn(self, value: str) -> None:
        """Handles a 'Learn' message"""
        self._storage.add(value)
        # TODO: pending writes

    async def _on_prepare(self, sender: uuid.UUID, proposal: int) -> None:
        """Handles a 'Prepare' message"""

        if self._promised is None or proposal > self._promised:
            self._promised = proposal

            await self._mediator.send(sender, message.Promise(
                proposal = self._promised,
                accepted = self._accepted.value,
                previous = self._accepted.proposal,
            ))
        else:
            await self._mediator.send(sender, message.Denied(
                reason = "Already promised to a higher proposal"
            ))

    async def _on_search(
        self,
        sender: uuid.UUID,
        value: str,
        recursive: bool,
    ) -> None:
        """Handles a 'Search' message"""

        if recursive:
            if value not in self._searching:
                self._searching[value] = _Searching(fails = 0, searchers = [])

            self._searching[value].searchers.append(sender)
            started = len(self._searching[value].searchers) == 1

            await self._mediator.send(sender, message.Acknowledge())

            if started:
                await self._mediator.broadcast(message.Search(
                    value = value,
                    recursive = False,
                ))
        else:
            await self._mediator.send(sender, message.Found(
                value = value,
                found = value in self._storage,
            ))

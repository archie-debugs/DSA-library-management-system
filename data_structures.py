"""Data structures used by the Library Management System."""

from collections import deque
from typing import Generic, TypeVar


QueueItem = TypeVar("QueueItem")

class OperationStack:
    """A simple LIFO stack for in-memory recent library activity."""

    def __init__(self) -> None:
        self._items: list[object] = []

    def push(self, item: object) -> None:
        """Add an item to the top of the stack."""
        self._items.append(item)

    def pop(self) -> object:
        """Remove and return the most recently pushed item."""
        if self.is_empty():
            raise IndexError("Cannot pop from an empty stack.")
        return self._items.pop()

    def peek(self) -> object:
        """Return the most recently pushed item without removing it."""
        if self.is_empty():
            raise IndexError("Cannot peek at an empty stack.")
        return self._items[-1]

    def is_empty(self) -> bool:
        """Return whether the stack contains no items."""
        return len(self._items) == 0

    def size(self) -> int:
        """Return the number of items currently in the stack."""
        return len(self._items)


class BorrowRequestQueue(Generic[QueueItem]):
    """A FIFO queue for pending borrowing requests."""

    def __init__(self) -> None:
        self._items: deque[QueueItem] = deque()

    def enqueue(self, item: QueueItem) -> None:
        """Add a request to the end of the queue."""
        self._items.append(item)

    def dequeue(self) -> QueueItem:
        """Remove and return the oldest request."""
        if self.is_empty():
            raise IndexError("Cannot dequeue from an empty queue.")
        return self._items.popleft()

    def peek(self) -> QueueItem:
        """Return the oldest request without removing it."""
        if self.is_empty():
            raise IndexError("Cannot peek at an empty queue.")
        return self._items[0]

    def to_list(self) -> list[QueueItem]:
        """Return a snapshot of requests in FIFO order."""
        return list(self._items)

    def remove(self, item: QueueItem) -> bool:
        """Remove the first matching request while preserving queue order."""
        found = False
        for _ in range(len(self._items)):
            queued_item = self._items.popleft()
            if not found and queued_item == item:
                found = True
            else:
                self._items.append(queued_item)
        return found

    def is_empty(self) -> bool:
        """Return whether the queue contains no requests."""
        return len(self._items) == 0

    def size(self) -> int:
        """Return the number of queued requests."""
        return len(self._items)

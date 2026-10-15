"""Tests for the manually implemented LIFO operation stack."""

import unittest
import tempfile
from pathlib import Path

from data_structures import BorrowRequestQueue, OperationStack
from library import Library
from main import activity_entries_newest_first


class DataStructuresTestCase(unittest.TestCase):
    def test_new_stack_is_empty(self) -> None:
        stack = OperationStack()
        self.assertTrue(stack.is_empty())
        self.assertEqual(stack.size(), 0)

    def test_push_pop_and_lifo_order(self) -> None:
        stack = OperationStack()
        stack.push("first")
        stack.push("second")
        self.assertEqual(stack.pop(), "second")
        self.assertEqual(stack.pop(), "first")
        self.assertTrue(stack.is_empty())

    def test_peek_returns_top_without_removing(self) -> None:
        stack = OperationStack()
        stack.push({"operation": "add"})
        self.assertEqual(stack.peek(), {"operation": "add"})
        self.assertEqual(stack.size(), 1)

    def test_size_and_empty_state_change(self) -> None:
        stack = OperationStack()
        stack.push("activity")
        self.assertFalse(stack.is_empty())
        self.assertEqual(stack.size(), 1)
        stack.pop()
        self.assertTrue(stack.is_empty())

    def test_empty_pop_and_peek_raise_index_error(self) -> None:
        stack = OperationStack()
        with self.assertRaises(IndexError):
            stack.pop()
        with self.assertRaises(IndexError):
            stack.peek()

    def test_stack_accepts_activity_records(self) -> None:
        stack = OperationStack()
        activity = {"operation": "search", "query": "python"}
        stack.push(activity)
        self.assertIs(stack.peek(), activity)

    def test_activity_view_is_newest_first_without_removing_entries(self) -> None:
        stack = OperationStack()
        stack.push("older")
        stack.push("newer")
        self.assertEqual(activity_entries_newest_first(stack), ["newer", "older"])
        self.assertEqual(stack.size(), 2)
        self.assertEqual(stack.peek(), "newer")

    def test_new_queue_is_empty(self) -> None:
        queue = BorrowRequestQueue()
        self.assertTrue(queue.is_empty())
        self.assertEqual(queue.size(), 0)

    def test_queue_processes_requests_in_fifo_order(self) -> None:
        queue = BorrowRequestQueue()
        queue.enqueue("first")
        queue.enqueue("second")
        self.assertEqual(queue.dequeue(), "first")
        self.assertEqual(queue.dequeue(), "second")
        self.assertTrue(queue.is_empty())

    def test_queue_peek_does_not_remove_next_request(self) -> None:
        queue = BorrowRequestQueue()
        queue.enqueue({"accession_no": "1"})
        self.assertEqual(queue.peek(), {"accession_no": "1"})
        self.assertEqual(queue.size(), 1)

    def test_queue_size_and_empty_state_change(self) -> None:
        queue = BorrowRequestQueue()
        queue.enqueue("request")
        self.assertFalse(queue.is_empty())
        self.assertEqual(queue.size(), 1)
        queue.dequeue()
        self.assertTrue(queue.is_empty())

    def test_queue_snapshot_preserves_order_and_removal_preserves_other_requests(self) -> None:
        queue = BorrowRequestQueue[dict[str, str]]()
        first_for_book = {"accession_no": "1", "borrower_name": "Alice"}
        other_book = {"accession_no": "2", "borrower_name": "Bob"}
        second_for_book = {"accession_no": "1", "borrower_name": "Casey"}
        queue.enqueue(first_for_book)
        queue.enqueue(other_book)
        queue.enqueue(second_for_book)

        self.assertEqual(queue.to_list(), [first_for_book, other_book, second_for_book])
        self.assertTrue(queue.remove(first_for_book))
        self.assertEqual(queue.to_list(), [other_book, second_for_book])
        self.assertFalse(queue.remove(first_for_book))

    def test_empty_queue_operations_raise_index_error(self) -> None:
        queue = BorrowRequestQueue()
        with self.assertRaises(IndexError):
            queue.dequeue()
        with self.assertRaises(IndexError):
            queue.peek()

    def test_invalid_request_does_not_block_later_valid_request(self) -> None:
        queue = BorrowRequestQueue()
        queue.enqueue(("missing", "Invalid"))
        queue.enqueue(("1", "Valid"))
        processed = []
        with tempfile.TemporaryDirectory() as directory:
            library = Library(Path(directory) / "queue.db")
            library.add_book(
                {
                    "call_no": "QA",
                    "title": "Queue Test",
                    "author": "Tester",
                    "publisher": "Test Press",
                    "copyright": "2020",
                    "locator": "Shelf",
                }
            )
            while not queue.is_empty():
                accession_no, borrower = queue.dequeue()
                try:
                    library.borrow_book(accession_no, borrower)
                except ValueError:
                    processed.append("rejected")
                else:
                    processed.append("accepted")
        self.assertEqual(processed, ["rejected", "accepted"])


if __name__ == "__main__":
    unittest.main()

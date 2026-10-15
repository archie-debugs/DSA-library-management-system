"""Tests for isolated, repeatable demonstration database startup."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from library import Library
from seed_demo_data import (
    DEMO_BOOKS,
    MAIN_DATABASE,
    ensure_demo_database,
    seed_demo_database,
)


class DemoDataTestCase(unittest.TestCase):
    def test_first_startup_seeds_once_and_repeated_startup_preserves_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library_demo.db"
            ensure_demo_database(path)
            library = Library(path)
            books = library.get_books()
            self.assertEqual(len(books), len(DEMO_BOOKS))
            self.assertEqual(
                [book["accession_no"] for book in books],
                [str(number) for number in range(1, len(DEMO_BOOKS) + 1)],
            )
            self.assertTrue(all(book["availability_status"] == "Available" for book in books))
            self.assertEqual(library.get_borrowing_records(), [])

            library.update_book("1", {**books[0], "title": "User Demonstration Change"})
            ensure_demo_database(path)
            self.assertEqual(Library(path).get_books()[0]["title"], "User Demonstration Change")

    def test_seed_marker_preserves_an_intentionally_empty_demo_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library_demo.db"
            ensure_demo_database(path)
            connection = sqlite3.connect(path)
            connection.execute("DELETE FROM books")
            connection.commit()
            connection.close()
            ensure_demo_database(path)
            self.assertEqual(Library(path).get_books(), [])

    def test_demo_borrowing_is_stored_only_in_demo_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            demo_path = Path(directory) / "library_demo.db"
            main_path = Path(directory) / "library.db"
            seed_demo_database(demo_path)
            demo_library = Library(demo_path)
            demo_library.borrow_book("1", "Demo Reader")
            self.assertEqual(demo_library.get_borrowing_records()[0]["accession_no"], "1")
            self.assertEqual(Library(main_path).get_books(), [])
            self.assertEqual(Library(main_path).get_borrowing_records(), [])

    def test_seed_rejects_the_main_database_path(self) -> None:
        with self.assertRaises(ValueError):
            seed_demo_database(MAIN_DATABASE)


if __name__ == "__main__":
    unittest.main()

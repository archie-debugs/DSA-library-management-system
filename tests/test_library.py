"""Tests for catalog persistence, migration, and borrowing workflows."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

import database
from library import Library


VALID_BOOK = {
    "call_no": "QA76.73",
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "publisher": "Prentice Hall",
    "copyright": "2008",
    "locator": "Shelf A",
}


class LibraryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_directory.name) / "test.db"
        self.library = Library(self.database_path)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_new_accessions_are_sequential_and_not_reused(self) -> None:
        self.library.add_book(VALID_BOOK)
        self.library.add_book({**VALID_BOOK, "title": "Algorithms"})
        self.assertEqual([book["accession_no"] for book in self.library.get_books()], ["1", "2"])
        self.assertTrue(self.library.delete_book("2"))
        self.library.add_book({**VALID_BOOK, "title": "Databases"})
        self.assertEqual([book["accession_no"] for book in self.library.get_books()], ["1", "3"])

    def test_all_catalog_fields_persist_after_reopen(self) -> None:
        self.library.add_book(VALID_BOOK)
        reopened = Library(self.database_path)
        record = reopened.get_books()[0]
        for field, value in VALID_BOOK.items():
            self.assertEqual(record[field], value)
        self.assertEqual(record["accession_no"], "1")
        self.assertEqual(record["availability_status"], "Available")

    def test_new_book_is_created_with_the_next_accession_number(self) -> None:
        self.library.add_book(VALID_BOOK)
        self.library.add_book({**VALID_BOOK, "title": "Algorithms"})

        books = self.library.get_books()
        self.assertEqual([book["accession_no"] for book in books], ["1", "2"])
        self.assertEqual(books[0]["title"], VALID_BOOK["title"])
        self.assertEqual(books[1]["title"], "Algorithms")

    def test_generated_call_numbers_repeat_until_saved_then_persist(self) -> None:
        first_suggestion = self.library.next_generated_call_no()
        self.assertEqual(first_suggestion, "QA76.10")
        self.assertEqual(self.library.next_generated_call_no(), first_suggestion)
        self.assertEqual(self.library.get_books(), [])

        self.library.add_book(
            {**VALID_BOOK, "call_no": first_suggestion},
            generated_call_no=True,
        )
        reopened = Library(self.database_path)
        self.assertEqual(reopened.get_books()[0]["call_no"], first_suggestion)
        self.assertEqual(reopened.next_generated_call_no(), "QC174.2")

    def test_generated_call_numbers_skip_existing_call_numbers_case_insensitively(self) -> None:
        self.library.add_book(
            {**VALID_BOOK, "call_no": "qa76.10"},
            generated_call_no=True,
        )
        assigned = {"qa76.10"}
        for number in range(1, len(database.CALL_NO_GENERATION_SERIES)):
            call_no = self.library.next_generated_call_no()
            self.assertNotIn(call_no.casefold(), assigned)
            self.library.add_book(
                {**VALID_BOOK, "call_no": call_no, "title": f"Generated {number}"},
                generated_call_no=True,
            )
            assigned.add(call_no.casefold())

        next_call_no = self.library.next_generated_call_no()
        self.assertEqual(next_call_no, "QA76.11")
        self.assertNotIn(next_call_no.casefold(), assigned)
        with self.assertRaisesRegex(ValueError, "already assigned"):
            self.library.add_book(
                {**VALID_BOOK, "call_no": "QA76.10", "title": "Duplicate"},
                generated_call_no=True,
            )
        self.assertEqual(len(self.library.get_books()), len(assigned))

    def test_required_fields_and_copyright_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            self.library.add_book({**VALID_BOOK, "title": ""})
        with self.assertRaises(ValueError):
            self.library.add_book({**VALID_BOOK, "copyright": "not-a-year"})
        with self.assertRaises(ValueError):
            self.library.add_book({**VALID_BOOK, "copyright": "3000"})
        self.assertEqual(self.library.get_books(), [])
        self.library.add_book(VALID_BOOK)
        self.assertEqual(self.library.get_books()[0]["accession_no"], "1")

    def test_update_preserves_accession_and_delete_missing_is_false(self) -> None:
        self.library.add_book(VALID_BOOK)
        updated = self.library.update_book("1", {**VALID_BOOK, "title": "Updated"})
        self.assertTrue(updated)
        self.assertEqual(self.library.get_books()[0]["accession_no"], "1")
        self.assertEqual(self.library.get_books()[0]["title"], "Updated")
        self.assertFalse(self.library.update_book("missing", VALID_BOOK))
        self.assertFalse(self.library.delete_book("missing"))

    def test_borrow_and_return_preserve_history(self) -> None:
        self.library.add_book(VALID_BOOK)
        self.assertIsNone(self.library.get_books()[0]["borrowed_by"])
        borrowed = self.library.borrow_book("1", "Alice")
        self.assertEqual(borrowed["accession_no"], "1")
        borrowed_book = self.library.get_books()[0]
        self.assertEqual(borrowed_book["availability_status"], "Borrowed")
        self.assertEqual(borrowed_book["borrowed_by"], "Alice")
        with self.assertRaises(ValueError):
            self.library.borrow_book("1", "Bob")
        with self.assertRaises(ValueError):
            self.library.delete_book("1")
        returned = self.library.return_book("1")
        self.assertEqual(returned["status"], "Returned")
        returned_book = self.library.get_books()[0]
        self.assertEqual(returned_book["availability_status"], "Available")
        self.assertIsNone(returned_book["borrowed_by"])
        records = self.library.get_borrowing_records()
        self.assertEqual(records[0]["accession_no"], "1")
        self.assertEqual(records[0]["borrower_name"], "Alice")
        self.assertEqual(records[0]["status"], "Returned")
        self.assertIsNotNone(records[0]["return_date"])
        with self.assertRaises(ValueError):
            self.library.delete_book("1")

    def test_active_borrower_is_restored_after_reopening_database(self) -> None:
        self.library.add_book(VALID_BOOK)
        self.library.borrow_book("1", "Morgan Reader")

        reopened = Library(self.database_path)
        book = reopened.get_books()[0]
        self.assertEqual(book["availability_status"], "Borrowed")
        self.assertEqual(book["borrowed_by"], "Morgan Reader")
        self.assertEqual(reopened.get_borrowing_records()[0]["borrower_name"], "Morgan Reader")

    def test_locator_choices_are_distinct_non_empty_and_alphabetical(self) -> None:
        self.library.add_book({**VALID_BOOK, "locator": "Shelf Z"})
        self.library.add_book(
            {**VALID_BOOK, "call_no": "QC174.2", "title": "Second", "locator": "Shelf A"}
        )
        self.library.add_book(
            {**VALID_BOOK, "call_no": "RA790.6", "title": "Third", "locator": "Shelf Z"}
        )
        database.add_book(
            {
                **VALID_BOOK,
                "accession_no": "4",
                "call_no": "BF698.6",
                "title": "Blank Locator",
                "locator": "   ",
            },
            self.database_path,
        )

        self.assertEqual(self.library.get_locators(), ["Shelf A", "Shelf Z"])

    def test_custom_locator_persists_and_existing_locator_changes_only_on_update(self) -> None:
        self.library.add_book(VALID_BOOK)
        self.library.add_book(
            {**VALID_BOOK, "call_no": "QC174.2", "title": "Second", "locator": "New Wing"}
        )
        self.assertEqual(
            [book["locator"] for book in self.library.get_books()],
            ["Shelf A", "New Wing"],
        )
        self.assertTrue(
            self.library.update_book("1", {**VALID_BOOK, "locator": "Upper Floor"})
        )

        reopened = Library(self.database_path)
        self.assertEqual(reopened.get_locators(), ["New Wing", "Upper Floor"])
        self.assertEqual(
            [book["locator"] for book in reopened.get_books()],
            ["Upper Floor", "New Wing"],
        )

    def test_missing_and_empty_borrowing_inputs_are_rejected(self) -> None:
        self.library.add_book(VALID_BOOK)
        with self.assertRaises(ValueError):
            self.library.borrow_book("missing", "Alice")
        with self.assertRaises(ValueError):
            self.library.borrow_book("1", "")
        with self.assertRaises(ValueError):
            self.library.return_book("missing")
        with self.assertRaises(ValueError):
            self.library.return_book("1")

    def test_legacy_schema_migrates_records_and_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.db"
            connection = sqlite3.connect(path)
            connection.executescript(
                """
                CREATE TABLE books (
                    book_id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    author TEXT NOT NULL, category TEXT NOT NULL,
                    publication_year INTEGER NOT NULL,
                    availability_status TEXT NOT NULL DEFAULT 'Available'
                );
                CREATE TABLE borrowing_records (
                    borrowing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id TEXT NOT NULL, borrower_name TEXT NOT NULL,
                    borrow_date TEXT NOT NULL, return_date TEXT,
                    status TEXT NOT NULL
                );
                INSERT INTO books VALUES ('B7', 'Legacy', 'Author', 'Old', 1999, 'Available');
                INSERT INTO borrowing_records
                    (book_id, borrower_name, borrow_date, status)
                    VALUES ('B7', 'Reader', '2024-01-01', 'Returned');
                """
            )
            connection.commit()
            connection.close()
            migrated = Library(path)
            book = migrated.get_books()[0]
            self.assertEqual(book["accession_no"], "B7")
            self.assertEqual(book["copyright"], "1999")
            self.assertEqual(migrated.get_borrowing_records()[0]["accession_no"], "B7")
            migrated.add_book(VALID_BOOK)
            self.assertEqual(migrated.get_books()[-1]["accession_no"], "1")


if __name__ == "__main__":
    unittest.main()

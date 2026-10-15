"""Business rules for book management."""

from datetime import datetime
from pathlib import Path
from typing import Any

import database


class Library:
    """Validate and coordinate book operations with SQLite."""

    def __init__(self, database_path: Path = database.DATABASE_PATH) -> None:
        self.database_path = database_path
        database.initialize_database(database_path)

    @staticmethod
    def validate_book(book: dict[str, Any]) -> dict[str, Any]:
        """Return normalized catalog data or raise ValueError for invalid input."""
        fields = ("call_no", "author", "title", "publisher", "locator")
        normalized = {field: str(book.get(field, "")).strip() for field in fields}
        if any(not normalized[field] for field in fields):
            raise ValueError("Call No., author, title, publisher, and locator are required.")
        copyright_year = str(book.get("copyright", "")).strip()
        if copyright_year:
            try:
                year = int(copyright_year)
            except ValueError as error:
                raise ValueError("Copyright must be a whole number when supplied.") from error
            if year < 1 or year > datetime.now().year:
                raise ValueError(f"Copyright must be between 1 and {datetime.now().year}.")
            copyright_year = str(year)
        normalized["copyright"] = copyright_year
        return normalized

    def add_book(self, book: dict[str, Any], *, generated_call_no: bool = False) -> None:
        normalized = self.validate_book(book)
        normalized["accession_no"] = database.next_accession_no(self.database_path)
        database.add_book(
            normalized,
            self.database_path,
            require_unique_call_no=generated_call_no,
        )

    def next_generated_call_no(self) -> str:
        """Suggest an unused automatic call number without reserving it."""
        return database.next_generated_call_no(self.database_path)

    def get_books(self) -> list[dict[str, Any]]:
        return database.get_books(self.database_path)

    def get_locators(self) -> list[str]:
        """Return saved locator choices for the configured database."""
        return database.get_locators(self.database_path)

    def update_book(self, accession_no: str, book: dict[str, Any]) -> bool:
        return database.update_book(
            accession_no,
            self.validate_book(book),
            self.database_path,
        )

    def delete_book(self, accession_no: str) -> bool:
        return database.delete_book(accession_no, self.database_path)

    @staticmethod
    def validate_borrower_name(borrower_name: str) -> str:
        """Validate and normalize a borrowing request's borrower name."""
        normalized = borrower_name.strip()
        if not normalized:
            raise ValueError("Borrower name is required.")
        return normalized

    def borrow_book(self, accession_no: str, borrower_name: str) -> dict[str, Any]:
        """Borrow an available book and persist its active borrowing record."""
        normalized_id = accession_no.strip()
        if not normalized_id:
            raise ValueError("Accession No. is required.")
        return database.borrow_book(
            normalized_id,
            self.validate_borrower_name(borrower_name),
            datetime.now().isoformat(timespec="seconds"),
            self.database_path,
        )

    def return_book(self, accession_no: str) -> dict[str, Any]:
        """Return a borrowed book and persist its return date."""
        normalized_id = accession_no.strip()
        if not normalized_id:
            raise ValueError("Accession No. is required.")
        return database.return_book(
            normalized_id,
            datetime.now().isoformat(timespec="seconds"),
            self.database_path,
        )

    def get_borrowing_records(self) -> list[dict[str, Any]]:
        """Return persisted borrowing records."""
        return database.get_borrowing_records(self.database_path)

"""SQLite database setup and persistence for catalog and borrowing records."""

import sqlite3
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(__file__).resolve().parent / "library.db"
# Fictional demo call-number patterns used for an administrative sequence.
# Each entry is (call-number stem, existing numeric suffix to continue from).
CALL_NO_GENERATION_SERIES = (
    ("QA76.", 9),
    ("QC174.", 1),
    ("RA790.", 5),
    ("BF698.", 5),
    ("PE", 1408),
    ("TT", 950),
    ("TK7881.", 4),
    ("TJ", 1185),
    ("HM", 585),
    ("HA31.", 2),
    ("T57.", 85),
    ("BJ", 1012),
    ("TA", 680),
    ("QA278.", 2),
)


def get_connection(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Open a connection to the application database."""
    return sqlite3.connect(database_path)


def _table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    """Create or safely migrate the application schema."""
    connection = get_connection(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        books_columns = _table_columns(connection, "books")
        if books_columns and "accession_no" not in books_columns:
            connection.execute("ALTER TABLE books RENAME TO books_legacy")
            connection.execute(
                """
                CREATE TABLE books (
                    accession_no TEXT PRIMARY KEY,
                    call_no TEXT NOT NULL DEFAULT '',
                    author TEXT NOT NULL,
                    title TEXT NOT NULL,
                    publisher TEXT NOT NULL DEFAULT '',
                    copyright TEXT NOT NULL DEFAULT '',
                    locator TEXT NOT NULL DEFAULT '',
                    availability_status TEXT NOT NULL DEFAULT 'Available'
                )
                """
            )
            connection.execute(
                """
                INSERT INTO books
                    (accession_no, call_no, author, title, publisher, copyright,
                     locator, availability_status)
                SELECT book_id, '', author, title, '', CAST(publication_year AS TEXT),
                       '', availability_status
                FROM books_legacy
                """
            )
            connection.execute("DROP TABLE books_legacy")
        elif not books_columns:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    accession_no TEXT PRIMARY KEY,
                    call_no TEXT NOT NULL DEFAULT '',
                    author TEXT NOT NULL,
                    title TEXT NOT NULL,
                    publisher TEXT NOT NULL DEFAULT '',
                    copyright TEXT NOT NULL DEFAULT '',
                    locator TEXT NOT NULL DEFAULT '',
                    availability_status TEXT NOT NULL DEFAULT 'Available'
                )
                """
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS accession_sequence (
                sequence_name TEXT PRIMARY KEY,
                next_no INTEGER NOT NULL
            )
            """
        )
        if connection.execute(
            "SELECT 1 FROM accession_sequence WHERE sequence_name = 'books'"
        ).fetchone() is None:
            values = connection.execute("SELECT accession_no FROM books").fetchall()
            numeric_values = []
            for (value,) in values:
                try:
                    numeric_values.append(int(value))
                except (TypeError, ValueError):
                    continue
            connection.execute(
                """
                INSERT INTO accession_sequence (sequence_name, next_no)
                VALUES ('books', ?)
                """,
                (max(numeric_values, default=0) + 1,),
            )

        borrowing_columns = _table_columns(connection, "borrowing_records")
        if not borrowing_columns:
            connection.execute(
                """
                CREATE TABLE borrowing_records (
                    borrowing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    accession_no TEXT NOT NULL,
                    borrower_name TEXT NOT NULL,
                    borrow_date TEXT NOT NULL,
                    return_date TEXT,
                    status TEXT NOT NULL CHECK (status IN ('Borrowed', 'Returned'))
                )
                """
            )
        elif "book_id" in borrowing_columns and "accession_no" not in borrowing_columns:
            connection.execute(
                "ALTER TABLE borrowing_records RENAME COLUMN book_id TO accession_no"
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def add_book(
    book: dict[str, Any],
    database_path: Path = DATABASE_PATH,
    *,
    require_unique_call_no: bool = False,
) -> None:
    """Insert one catalog record using a parameterized query."""
    connection = get_connection(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        call_no = str(book["call_no"])
        if require_unique_call_no:
            existing = connection.execute(
                "SELECT 1 FROM books WHERE call_no = ? COLLATE NOCASE",
                (call_no,),
            ).fetchone()
            if existing is not None:
                raise ValueError(
                    f"Generated Call No. '{call_no}' is already assigned. "
                    "Click Add to generate another."
                )
        connection.execute(
            """
            INSERT INTO books
                (accession_no, call_no, author, title, publisher, copyright, locator)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(book[field] for field in (
                "accession_no", "call_no", "author", "title",
                "publisher", "copyright", "locator",
            )),
        )
        connection.commit()
    finally:
        connection.close()


def next_generated_call_no(database_path: Path = DATABASE_PATH) -> str:
    """Suggest a unique classification-style call number without reserving it."""
    connection = get_connection(database_path)
    try:
        call_numbers = connection.execute("SELECT call_no FROM books").fetchall()
    finally:
        connection.close()

    existing = {str(row[0]).casefold() for row in call_numbers}
    series_index = len(call_numbers) % len(CALL_NO_GENERATION_SERIES)
    stem, initial_number = CALL_NO_GENERATION_SERIES[series_index]
    highest_number = initial_number
    for (value,) in call_numbers:
        call_no = str(value)
        if not call_no.casefold().startswith(stem.casefold()):
            continue
        suffix = call_no[len(stem):]
        if suffix.isdecimal():
            highest_number = max(highest_number, int(suffix))

    candidate_number = highest_number + 1
    while True:
        candidate = f"{stem}{candidate_number}"
        if candidate.casefold() not in existing:
            return candidate
        candidate_number += 1


def next_accession_no(database_path: Path = DATABASE_PATH) -> str:
    """Reserve and return the next sequential numeric accession number."""
    connection = get_connection(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT next_no FROM accession_sequence WHERE sequence_name = 'books'"
        ).fetchone()
        if row is None:
            raise sqlite3.Error("Accession sequence is not initialized.")
        connection.execute(
            """
            UPDATE accession_sequence SET next_no = next_no + 1
            WHERE sequence_name = 'books'
            """
        )
        connection.commit()
        return str(row[0])
    except sqlite3.Error:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_books(database_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """Return all catalog records."""
    connection = get_connection(database_path)
    try:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT accession_no, call_no, author, title, publisher, copyright,
                   locator, availability_status,
                   (
                       SELECT borrower_name
                       FROM borrowing_records
                       WHERE borrowing_records.accession_no = books.accession_no
                         AND status = 'Borrowed'
                       ORDER BY borrowing_id DESC
                       LIMIT 1
                   ) AS borrowed_by
            FROM books
            ORDER BY CAST(accession_no AS INTEGER), accession_no
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_locators(database_path: Path = DATABASE_PATH) -> list[str]:
    """Return distinct, non-empty stored locators in alphabetical order."""
    connection = get_connection(database_path)
    try:
        rows = connection.execute(
            """
            SELECT DISTINCT locator
            FROM books
            WHERE TRIM(locator) <> ''
            ORDER BY locator COLLATE NOCASE, locator
            """
        ).fetchall()
        return [str(row[0]) for row in rows]
    finally:
        connection.close()


def update_book(
    accession_no: str,
    book: dict[str, Any],
    database_path: Path = DATABASE_PATH,
) -> bool:
    """Update catalog details without changing the accession number."""
    connection = get_connection(database_path)
    try:
        cursor = connection.execute(
            """
            UPDATE books
            SET call_no = ?, author = ?, title = ?, publisher = ?,
                copyright = ?, locator = ?
            WHERE accession_no = ?
            """,
            (
                book["call_no"], book["author"], book["title"], book["publisher"],
                book["copyright"], book["locator"], accession_no,
            ),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def delete_book(accession_no: str, database_path: Path = DATABASE_PATH) -> bool:
    """Delete a record only when it has no borrowing history."""
    connection = get_connection(database_path)
    try:
        history = connection.execute(
            "SELECT 1 FROM borrowing_records WHERE accession_no = ?",
            (accession_no,),
        ).fetchone()
        if history is not None:
            raise ValueError("A book with borrowing history cannot be deleted.")
        cursor = connection.execute(
            "DELETE FROM books WHERE accession_no = ?", (accession_no,)
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def borrow_book(
    accession_no: str,
    borrower_name: str,
    borrow_date: str,
    database_path: Path = DATABASE_PATH,
) -> dict[str, Any]:
    """Borrow an available record and create its active record atomically."""
    connection = get_connection(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        book = connection.execute(
            "SELECT availability_status FROM books WHERE accession_no = ?",
            (accession_no,),
        ).fetchone()
        if book is None:
            raise ValueError(f"Accession No. '{accession_no}' does not exist.")
        if book[0] != "Available":
            raise ValueError(f"Accession No. '{accession_no}' is currently unavailable.")
        connection.execute(
            "UPDATE books SET availability_status = 'Borrowed' WHERE accession_no = ?",
            (accession_no,),
        )
        cursor = connection.execute(
            """
            INSERT INTO borrowing_records
                (accession_no, borrower_name, borrow_date, status)
            VALUES (?, ?, ?, 'Borrowed')
            """,
            (accession_no, borrower_name, borrow_date),
        )
        connection.commit()
        return {
            "borrowing_id": cursor.lastrowid, "accession_no": accession_no,
            "borrower_name": borrower_name, "borrow_date": borrow_date,
            "return_date": None, "status": "Borrowed",
        }
    except (sqlite3.Error, ValueError):
        connection.rollback()
        raise
    finally:
        connection.close()


def return_book(
    accession_no: str,
    return_date: str,
    database_path: Path = DATABASE_PATH,
) -> dict[str, Any]:
    """Return a borrowed record and close its active record atomically."""
    connection = get_connection(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        book = connection.execute(
            "SELECT availability_status FROM books WHERE accession_no = ?",
            (accession_no,),
        ).fetchone()
        if book is None:
            raise ValueError(f"Accession No. '{accession_no}' does not exist.")
        if book[0] != "Borrowed":
            raise ValueError(f"Accession No. '{accession_no}' is already available.")
        record = connection.execute(
            """
            SELECT borrowing_id, borrower_name, borrow_date
            FROM borrowing_records
            WHERE accession_no = ? AND status = 'Borrowed'
            ORDER BY borrowing_id DESC LIMIT 1
            """,
            (accession_no,),
        ).fetchone()
        if record is None:
            raise ValueError(f"Accession No. '{accession_no}' has no active record.")
        connection.execute(
            """
            UPDATE borrowing_records
            SET return_date = ?, status = 'Returned'
            WHERE borrowing_id = ?
            """,
            (return_date, record[0]),
        )
        connection.execute(
            "UPDATE books SET availability_status = 'Available' WHERE accession_no = ?",
            (accession_no,),
        )
        connection.commit()
        return {
            "borrowing_id": record[0], "accession_no": accession_no,
            "borrower_name": record[1], "borrow_date": record[2],
            "return_date": return_date, "status": "Returned",
        }
    except (sqlite3.Error, ValueError):
        connection.rollback()
        raise
    finally:
        connection.close()


def get_borrowing_records(database_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    """Return borrowing history in creation order."""
    connection = get_connection(database_path)
    try:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT borrowing_id, accession_no, borrower_name, borrow_date,
                   return_date, status
            FROM borrowing_records
            ORDER BY borrowing_id
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()

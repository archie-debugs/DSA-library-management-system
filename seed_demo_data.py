"""Create a separate fictional demonstration catalog database."""

import argparse
import sqlite3
from pathlib import Path

from library import Library


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DEMO_DATABASE = PROJECT_ROOT / "library_demo.db"
MAIN_DATABASE = PROJECT_ROOT / "library.db"
SEED_MARKER_TABLE = "demo_seed_metadata"

# These are explicitly fictional demonstration records, designed to exercise
# the catalog fields and search/sort workflows without importing the catalog.
DEMO_BOOKS = (
    ("QA76.9", "Demonstration Author", "Foundations of Artificial Intelligence", "Demo Academic Press", "2024", "General Reference"),
    ("QC174.1", "Demonstration Author", "An Introduction to Quantum Computing", "Demo Technical Press", "2023", "General Reference"),
    ("RA790.5", "Demonstration Author", "Perspectives in Mental Health Care", "Demo Health Press", "2022", "Health Sciences"),
    ("BF698.5", "Demonstration Author", "Applied Health Psychology", "Demo Health Press", "2021", "Health Sciences"),
    ("PE1408", "Demonstration Author", "Purposive Communication Workshop", "Demo Academic Press", "2024", "Language"),
    ("TT950", "Demonstration Author", "Principles of Hair Styling", "Demo Skills Press", "2020", "Skills Laboratory"),
    ("TK7881.4", "Demonstration Author", "Audio Engineering Essentials", "Demo Technical Press", "2023", "Media Laboratory"),
    ("TJ1185", "Demonstration Author", "Machining and Welding Practice", "Demo Technical Press", "2022", "Engineering Workshop"),
    ("QA76.9", "Demonstration Author", "Designing Data-Intensive Applications", "Demo Computing Press", "2024", "Computing Reference"),
    ("HM585", "Demonstration Author", "Contemporary Sociological Theory", "Demo Social Science Press", "2021", "Social Sciences"),
    ("HA31.2", "Demonstration Author", "Survey Design Methods", "Demo Social Science Press", "2020", "Research Methods"),
    ("T57.85", "Demonstration Author", "Machine Learning for Urban Design", "Demo Computing Press", "2024", "Architecture Reference"),
    ("QC522", "Demonstration Author", "Practical Electromagnetism", "Demo Technical Press", "2022", "Engineering Reference"),
    ("TJ1180", "Demonstration Author", "Cutting Tools and Materials", "Demo Technical Press", "2021", "Engineering Workshop"),
    ("BJ1012", "Demonstration Author", "Questions in Moral Philosophy", "Demo Humanities Press", "2023", "Humanities"),
    ("TA680", "Demonstration Author", "Engineering Mechanics in Practice", "Demo Technical Press", "2022", "Engineering Reference"),
    ("QA76.6", "Demonstration Author", "Computer Coding Fundamentals", "Demo Computing Press", "2024", "Computing Laboratory"),
    ("TS171", "Demonstration Author", "Introduction to 3D Printing", "Demo Skills Press", "2023", "Fabrication Laboratory"),
    ("QA278.2", "Demonstration Author", "Understanding Correlation Matrices", "Demo Social Science Press", "2020", "Research Methods"),
    ("PE1112", "Demonstration Author", "Syntax and Phonics Activities", "Demo Academic Press", "2021", "Language"),
)


def seed_demo_database(database_path: Path = DEFAULT_DEMO_DATABASE) -> list[str]:
    """Insert missing fictional records and return their assigned accessions."""
    if database_path.resolve() == MAIN_DATABASE.resolve():
        raise ValueError("The demonstration seed cannot target library.db.")
    library = Library(database_path)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SEED_MARKER_TABLE} (
                seed_name TEXT PRIMARY KEY,
                seeded_at TEXT NOT NULL
            )
            """
        )
        if connection.execute(
            f"SELECT 1 FROM {SEED_MARKER_TABLE} WHERE seed_name = ?",
            ("catalog-demo-v1",),
        ).fetchone():
            connection.commit()
            return []
        connection.commit()
    finally:
        connection.close()

    existing = library.get_books()
    existing_keys = {
        (book["call_no"], book["author"], book["title"], book["publisher"],
         book["copyright"], book["locator"])
        for book in existing
    }
    inserted: list[str] = []
    for call_no, author, title, publisher, copyright_year, locator in DEMO_BOOKS:
        key = (call_no, author, title, publisher, copyright_year, locator)
        if key in existing_keys:
            continue
        library.add_book(
            {
                "call_no": call_no,
                "author": author,
                "title": title,
                "publisher": publisher,
                "copyright": copyright_year,
                "locator": locator,
            }
        )
        new_book = next(
            book for book in library.get_books()
            if (book["call_no"], book["author"], book["title"], book["publisher"],
                book["copyright"], book["locator"]) == key
        )
        existing_keys.add(key)
        if new_book["availability_status"] != "Available":
            raise sqlite3.Error("Newly seeded demo record is not Available.")
        inserted.append(new_book["accession_no"])

    books = library.get_books()
    if len(books) < len(DEMO_BOOKS):
        raise sqlite3.Error("Demo database contains fewer records than the seed dataset.")
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            f"INSERT INTO {SEED_MARKER_TABLE} (seed_name, seeded_at) VALUES (?, datetime('now'))",
            ("catalog-demo-v1",),
        )
        connection.commit()
    finally:
        connection.close()
    return inserted


def ensure_demo_database(database_path: Path = DEFAULT_DEMO_DATABASE) -> None:
    """Create and seed the demo database once, preserving later user changes."""
    seed_demo_database(database_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create fictional demo catalog records.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DEMO_DATABASE)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the selected demo database before seeding.",
    )
    parser.add_argument(
        "--confirm-reset",
        action="store_true",
        help="Required with --reset to explicitly authorize deletion.",
    )
    args = parser.parse_args()
    if args.database.resolve() == MAIN_DATABASE.resolve():
        parser.error("The demonstration seed cannot target library.db")
    if args.reset:
        if not args.confirm_reset:
            parser.error("--reset requires --confirm-reset")
        if args.database.exists():
            args.database.unlink()
    inserted = seed_demo_database(args.database)
    books = Library(args.database).get_books()
    print(f"Demo database: {args.database}")
    print(f"Total demonstration records: {len(books)}")
    print(f"New records inserted: {len(inserted)}")
    print(f"Assigned Accession Numbers: {', '.join(inserted) if inserted else 'none'}")
    print("All seeded records are fictional demonstration data and Available.")


if __name__ == "__main__":
    main()

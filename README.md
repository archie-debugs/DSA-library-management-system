# Library Management System

A small desktop library catalog application for an academic Python data
structures and algorithms project. It uses Tkinter/ttk and SQLite, with no
third-party dependencies.

## Catalog fields and features

Each book has an automatically assigned, unique **Accession No.**, followed by
Call No., Author, Title, Publisher, Copyright, Locator, and Availability
Status. New accession numbers start at 1 and continue above the highest
existing numeric accession number; deleted numbers are never reused. The
accession number is read-only during updates.

Selecting **Add** suggests a unique Call No. from the configurable
`CALL_NO_GENERATION_SERIES` in `database.py`. It rotates through configured
catalog stems (for example, `QA76.`, `QC174.`, `RA790.`, and
`BF698.`) and advances the numeric suffix for the selected stem, yielding
values such as `QA76.10`, `QC174.2`, and `RA790.6`. Existing saved values are
skipped. These values only resemble the catalog's Library-of-Congress-style
notation; the application cannot infer a book's subject or assign
professionally verified classifications. They are administrative identifiers,
not subject classifications. Suggestions depend only on saved records and
are not reserved until saving, so repeated Add clicks do not consume sequence
numbers. Existing Call Nos. are unchanged.

The application supports adding, displaying, updating, deleting eligible
records, searching, title sorting, borrowing, returning, a visible FIFO waiting
list for borrowed books, dashboard counts, Recent Activity, and persistent
borrowing history. When a borrowed book is requested, its request is added to
the waiting list. On return, the app confirms whether each queued borrower is
available before lending the book. Confirming Yes lends it to that person;
selecting No skips and removes that request, then offers the book to the next
request for that accession number. Cancel leaves the current request queued and
the book available. Books with any borrowing history cannot be deleted.

## Project structure

- `main.py` — Tkinter form, table, controls, dashboard, and dialogs.
- `library.py` — validation and business rules.
- `database.py` — SQLite schema, migration, parameterized queries, and
  transactions.
- `algorithms.py` — manual Linear Search and Insertion Sort.
- `data_structures.py` — LIFO `OperationStack` and FIFO
  `BorrowRequestQueue`.
- `seed_demo_data.py` — repeatable setup for the demonstration catalog.
- `tests/` — temporary-database `unittest` coverage.

## Algorithms and data structures

Linear Search is a manual loop. Accession No. uses exact matching, while
Title and Author use case-insensitive partial matching. Insertion Sort is
implemented manually and returns a copy ordered by a selected field. Use the
catalog's **Sort by** and **Ascending/Descending** dropdowns to sort by
Accession No., Call No., Author, Title, Publisher, Copyright, Locator,
Availability Status, or Borrowed By. Text sorting ignores case; numeric
Accession No. and Copyright values sort numerically, with empty numeric values
last. Linear Search and Insertion Sort have time complexities O(n) and O(n²),
respectively.

Book records retrieved from SQLite are processed as a list. Recent Activity
uses a Stack (LIFO: newest entry first), and pending borrow requests use a Queue
(FIFO: oldest request for a returned book first). The **Borrow Queue** window
shows pending requests in order and includes a case-insensitive filter. Choose
All Fields or a specific field (position, accession number, title, borrower, or
request time) from the dropdown, then type a search term. Filtering only
changes what is displayed; it does not change queue order. The queue is in
memory, so pending requests are lost when the application closes.

## Basic GUI workflow

1. Select **Add** to clear the form, start a new entry, and display a suggested
   classification-style Call No.
2. Enter Author, Title, Publisher, Copyright, and Locator, then select
   **Save Book**. The Accession No. is assigned automatically.
3. Select a row to populate the form, then edit and select **Update**.
4. Use **Search** with Accession No., Title, or Author. Choose a field and
   direction in the **Sort by** dropdowns, then select **Sort**.
5. Select an eligible row and choose **Delete**.
6. Select an available row, choose **Borrow**, and enter a borrower name.
7. Select the borrowed row, choose **Borrow** again, and enter another name to
   add a waiting request. Open **Borrow Queue** to see and filter the pending
   requests by choosing a visible field from the filter dropdown.
8. Choose **Return** for that book. Confirm whether each queued borrower is
   available; choose No to skip an unavailable person, Yes to lend to them, or
   Cancel to leave the request queued and the book available.
9. Open **Recent Activity** to see successful operations newest-first.

## Limitations

Recent Activity and queued requests are in-memory and disappear when the
application closes. The GUI intentionally has no login, networking, barcode,
reporting, or cloud features. Actual collection data has not been entered.

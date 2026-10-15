"""Tkinter user interface for the Library Management System."""

import argparse
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import sqlite3
from datetime import datetime
from pathlib import Path

from algorithms import insertion_sort_by, linear_search
from data_structures import BorrowRequestQueue, OperationStack
import database
from library import Library
from seed_demo_data import DEFAULT_DEMO_DATABASE, ensure_demo_database


WINDOW_TITLE = "Library Management System"
PLACEHOLDER_MESSAGE = "This feature will be implemented in a later phase."


def show_placeholder(feature: str) -> None:
    """Explain that a control is reserved for a later implementation phase."""
    messagebox.showinfo(feature, f"{feature} is not available yet.\n{PLACEHOLDER_MESSAGE}")


def activity_entries_newest_first(activity_stack: OperationStack) -> list[str]:
    """Read stack entries newest-first and restore the stack unchanged."""
    entries: list[str] = []
    while not activity_stack.is_empty():
        entries.append(str(activity_stack.pop()))
    for entry in reversed(entries):
        activity_stack.push(entry)
    return entries


def create_book_form(
    parent: ttk.Frame,
) -> tuple[ttk.LabelFrame, dict[str, ttk.Entry | ttk.Combobox]]:
    """Create the catalog form and return its fields."""
    form = ttk.LabelFrame(parent, text="Book Information", padding=10)
    field_names = (
        ("accession_no", "Accession No."),
        ("call_no", "Call No."),
        ("author", "Author"),
        ("title", "Title"),
        ("publisher", "Publisher"),
        ("copyright", "Copyright"),
        ("locator", "Locator"),
    )
    entries: dict[str, ttk.Entry | ttk.Combobox] = {}

    for row, (name, field) in enumerate(field_names):
        ttk.Label(form, text=f"{field}:").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
        if name == "locator":
            entry: ttk.Entry | ttk.Combobox = ttk.Combobox(
                form,
                width=26,
                state="normal",
            )
        else:
            entry = ttk.Entry(
                form,
                width=28,
                state="readonly" if name == "accession_no" else "normal",
            )
        entry.grid(row=row, column=1, sticky="ew", pady=3)
        entries[name] = entry

    form.columnconfigure(1, weight=1)
    return form, entries


def create_application(database_path: Path = DEFAULT_DEMO_DATABASE) -> tk.Tk:
    """Create the initial application window and its interface."""
    if database_path.resolve() == DEFAULT_DEMO_DATABASE.resolve():
        ensure_demo_database(database_path)
    root = tk.Tk()
    root.title(WINDOW_TITLE)
    root.geometry("1100x700")
    root.minsize(850, 550)
    library = Library(database_path)
    activity_stack = OperationStack()
    borrow_queue: BorrowRequestQueue[dict[str, str]] = BorrowRequestQueue()
    queue_window: tk.Toplevel | None = None
    queue_table: ttk.Treeview | None = None
    queue_empty_state: ttk.Label | None = None
    queue_filter_entry: ttk.Entry | None = None
    queue_filter_field: ttk.Combobox | None = None

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    container = ttk.Frame(root, padding=12)
    container.grid(row=0, column=0, sticky="nsew")
    container.columnconfigure(0, weight=1)
    container.rowconfigure(2, weight=1)

    ttk.Label(container, text=WINDOW_TITLE, font=("TkDefaultFont", 16, "bold")).grid(
        row=0, column=0, sticky="w", pady=(0, 10)
    )

    dashboard = ttk.LabelFrame(container, text="Dashboard", padding=10)
    dashboard.grid(row=1, column=0, sticky="ew", pady=(0, 10))
    dashboard.columnconfigure(0, weight=1)
    dashboard.columnconfigure(1, weight=1)
    for column, label in enumerate(("Total Books", "Available Books")):
        card = ttk.Frame(dashboard, padding=5)
        card.grid(row=0, column=column, sticky="ew")
        ttk.Label(card, text=label, font=("TkDefaultFont", 10, "bold")).pack()
        value_label = ttk.Label(card, text="0")
        value_label.pack(pady=(4, 0))
        if label == "Total Books":
            total_books_label = value_label
        else:
            available_books_label = value_label

    management = ttk.LabelFrame(container, text="Book Management", padding=10)
    management.grid(row=2, column=0, sticky="nsew")
    management.columnconfigure(0, weight=1)
    management.rowconfigure(2, weight=1)

    search_bar = ttk.Frame(management)
    search_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    search_bar.columnconfigure(2, weight=1)
    ttk.Label(search_bar, text="Search:").grid(row=0, column=0, padx=(0, 8))
    search_field = ttk.Combobox(
        search_bar,
        values=("Accession No.", "Title", "Author"),
        state="readonly",
        width=10,
    )
    search_field.set("Title")
    search_field.grid(row=0, column=1, padx=(0, 8))
    search_entry = ttk.Entry(search_bar)
    search_entry.grid(row=0, column=2, sticky="ew")
    ttk.Button(
        search_bar,
        text="Search",
        command=lambda: search_books(),
    ).grid(row=0, column=3, padx=(8, 0))
    ttk.Label(search_bar, text="Sort by:").grid(row=1, column=0, sticky="w", pady=(5, 0))
    sort_field = ttk.Combobox(
        search_bar,
        values=(
            "Accession No.",
            "Call No.",
            "Author",
            "Title",
            "Publisher",
            "Copyright",
            "Locator",
            "Availability Status",
            "Borrowed By",
        ),
        state="readonly",
        width=18,
    )
    sort_field.set("Title")
    sort_field.grid(row=1, column=1, sticky="w", padx=(0, 8), pady=(5, 0))
    sort_direction = ttk.Combobox(
        search_bar,
        values=("Ascending", "Descending"),
        state="readonly",
        width=12,
    )
    sort_direction.set("Ascending")
    sort_direction.grid(row=1, column=2, sticky="w", pady=(5, 0))
    ttk.Button(
        search_bar,
        text="Sort",
        command=lambda: sort_books(),
    ).grid(row=1, column=3, padx=(8, 0), pady=(5, 0))

    columns = (
        "accession_no", "call_no", "author", "title", "publisher",
        "copyright", "locator", "status", "borrowed_by",
    )
    table = ttk.Treeview(management, columns=columns, show="headings", height=10)
    headings = {
        "accession_no": "Accession No.",
        "call_no": "Call No.",
        "author": "Author",
        "title": "Title",
        "publisher": "Publisher",
        "copyright": "Copyright",
        "locator": "Locator",
        "status": "Availability Status",
        "borrowed_by": "Borrowed By",
    }
    widths = {"accession_no": 110, "call_no": 110, "author": 150, "title": 180,
              "publisher": 150, "copyright": 90, "locator": 110, "status": 150,
              "borrowed_by": 150}
    for column in columns:
        table.heading(column, text=headings[column])
        table.column(column, width=widths[column], anchor="w")
    table.grid(row=2, column=0, sticky="nsew")
    scrollbar = ttk.Scrollbar(management, orient="vertical", command=table.yview)
    scrollbar.grid(row=2, column=1, sticky="ns")
    table.configure(yscrollcommand=scrollbar.set)
    horizontal_scrollbar = ttk.Scrollbar(management, orient="horizontal", command=table.xview)
    horizontal_scrollbar.grid(row=3, column=0, sticky="ew")
    table.configure(xscrollcommand=horizontal_scrollbar.set)
    empty_state = ttk.Label(management, text="No book records to display.")
    empty_state.grid(row=4, column=0, sticky="w", pady=(6, 0))

    controls = ttk.Frame(management)
    controls.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    form, entries = create_book_form(container)
    form.grid(row=3, column=0, sticky="ew", pady=(10, 0))
    selected_accession_no: str | None = None
    save_in_progress = False

    def read_form() -> dict[str, str]:
        return {name: entry.get() for name, entry in entries.items()}

    def refresh_locator_choices() -> None:
        try:
            locators = library.get_locators()
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", f"Could not load locators: {error}")
            return
        locator_entry = entries["locator"]
        if isinstance(locator_entry, ttk.Combobox):
            locator_entry.configure(values=locators)

    def clear_form() -> None:
        nonlocal selected_accession_no
        selected_accession_no = None
        for entry in entries.values():
            if str(entry.cget("state")) == "readonly":
                entry.configure(state="normal")
            entry.delete(0, tk.END)
            if entry is entries["accession_no"]:
                entry.configure(state="readonly")
            elif entry is entries["call_no"]:
                entry.configure(state="normal")

    def populate_books(books: list[dict]) -> None:
        for item in table.get_children():
            table.delete(item)
        for book in books:
            table.insert(
                "",
                tk.END,
                values=(
                    book["accession_no"],
                    book["call_no"],
                    book["author"],
                    book["title"],
                    book["publisher"],
                    book["copyright"],
                    book["locator"],
                    book["availability_status"],
                    book["borrowed_by"] or "—",
                ),
            )
        empty_state.grid_remove() if books else empty_state.grid()

    def record_activity(description: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        activity_stack.push(f"{timestamp} - {description}")

    def refresh_books() -> None:
        try:
            books = library.get_books()
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", f"Could not load books: {error}")
            return
        populate_books(books)
        total_books_label.config(text=str(len(books)))
        available_books_label.config(
            text=str(sum(book["availability_status"] == "Available" for book in books))
        )

    def select_table_book(accession_no: str) -> None:
        """Select a book after a refresh so the next action targets it."""
        for item in table.get_children():
            values = table.item(item, "values")
            if values and str(values[0]) == accession_no:
                table.selection_set(item)
                table.focus(item)
                table.see(item)
                return

    def search_books() -> None:
        query = search_entry.get().strip()
        if not query:
            refresh_books()
            return
        field_names = {"Accession No.": "accession_no", "Title": "title", "Author": "author"}
        try:
            books = library.get_books()
            matches = linear_search(books, query, field_names[search_field.get()])
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", f"Could not search books: {error}")
            return
        populate_books(matches)
        record_activity(f"Search {search_field.get()} for '{query}' ({len(matches)} result(s))")
        if not matches:
            messagebox.showinfo("No Results", "No books matched the search.")

    def sort_books() -> None:
        try:
            books = library.get_books()
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", f"Could not sort books: {error}")
            return
        field_names = {
            "Accession No.": "accession_no",
            "Call No.": "call_no",
            "Author": "author",
            "Title": "title",
            "Publisher": "publisher",
            "Copyright": "copyright",
            "Locator": "locator",
            "Availability Status": "availability_status",
            "Borrowed By": "borrowed_by",
        }
        selected_field = sort_field.get()
        descending = sort_direction.get() == "Descending"
        sorted_books = insertion_sort_by(
            books,
            field_names[selected_field],
            descending=descending,
        )
        populate_books(sorted_books)
        record_activity(
            f"Sorted books by {selected_field} ({sort_direction.get().lower()})"
        )

    def prepare_new_book() -> None:
        clear_form()
        selection = table.selection()
        if selection:
            table.selection_remove(*selection)
        try:
            call_no = library.next_generated_call_no()
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", f"Could not generate a Call No.: {error}")
            return
        entries["call_no"].configure(state="normal")
        entries["call_no"].insert(0, call_no)
        entries["call_no"].configure(state="readonly")
        entries["author"].focus_set()

    def save_book() -> None:
        nonlocal save_in_progress
        if save_in_progress:
            return
        save_in_progress = True
        save_button.configure(state="disabled")
        try:
            library.add_book(read_form(), generated_call_no=True)
        except ValueError as error:
            messagebox.showerror("Invalid Book", str(error))
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate Accession No.", "The accession number is assigned automatically.")
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", f"Could not add book: {error}")
        else:
            clear_form()
            refresh_books()
            refresh_locator_choices()
            record_activity("Added a book")
            messagebox.showinfo("Book Added", "The book was added successfully.")
        finally:
            save_in_progress = False
            save_button.configure(state="normal")

    def select_book(_event: tk.Event) -> None:
        nonlocal selected_accession_no
        selection = table.selection()
        if not selection:
            return
        values = table.item(selection[0], "values")
        selected_accession_no = str(values[0])
        for name, value in zip(entries, values):
            if name in ("accession_no", "call_no"):
                entries[name].configure(state="normal")
            entries[name].delete(0, tk.END)
            entries[name].insert(0, value)
            if name == "accession_no":
                entries[name].configure(state="readonly")

    def update_book() -> None:
        if selected_accession_no is None:
            messagebox.showerror("No Selection", "Select a book to update.")
            return
        accession_no = selected_accession_no
        try:
            updated = library.update_book(accession_no, read_form())
        except ValueError as error:
            messagebox.showerror("Invalid Book", str(error))
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", f"Could not update book: {error}")
        else:
            if not updated:
                messagebox.showerror("Missing Book", "The selected book no longer exists.")
                return
            clear_form()
            refresh_books()
            refresh_locator_choices()
            record_activity(f"Updated book '{accession_no}'")
            messagebox.showinfo("Book Updated", "The book was updated successfully.")

    def delete_book() -> None:
        selection = table.selection()
        if not selection:
            messagebox.showerror("No Selection", "Select a book to delete.")
            return
        accession_no = str(table.item(selection[0], "values")[0])
        if not messagebox.askyesno("Confirm Delete", f"Delete book '{accession_no}'?"):
            return
        try:
            deleted = library.delete_book(accession_no)
        except ValueError as error:
            messagebox.showerror("Cannot Delete Book", str(error))
            return
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", f"Could not delete book: {error}")
            return
        if not deleted:
            messagebox.showerror("Missing Book", "The selected book no longer exists.")
            return
        clear_form()
        refresh_locator_choices()
        refresh_books()
        record_activity(f"Deleted book '{accession_no}'")
        messagebox.showinfo("Book Deleted", "The book was deleted successfully.")

    def borrow_selected_book() -> None:
        selection = table.selection()
        if not selection:
            messagebox.showerror("No Selection", "Select a book to borrow or join its waiting list.")
            return
        values = table.item(selection[0], "values")
        accession_no = str(values[0])
        title = str(values[3])
        is_borrowed = str(values[7]) == "Borrowed"
        borrower_name = simpledialog.askstring(
            "Join Borrow Queue" if is_borrowed else "Borrow Book",
            (
                f"Borrower name to queue for '{title}' (accession '{accession_no}'):"
                if is_borrowed
                else f"Borrower name for accession '{accession_no}':"
            ),
            parent=root,
        )
        if borrower_name is None:
            return
        try:
            borrower_name = library.validate_borrower_name(borrower_name)
        except ValueError as error:
            messagebox.showerror("Invalid Borrower", str(error))
            return
        if is_borrowed:
            request = {
                "accession_no": accession_no,
                "borrower_name": borrower_name,
                "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            borrow_queue.enqueue(request)
            refresh_borrow_queue()
            record_activity(f"Queued borrow request for '{accession_no}'")
            messagebox.showinfo(
                "Request Queued",
                f"{borrower_name} was added to the waiting list for '{title}'.",
            )
            return
        try:
            result = library.borrow_book(accession_no, borrower_name)
        except ValueError as error:
            messagebox.showerror("Cannot Borrow Book", str(error))
            return
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", f"Could not borrow book: {error}")
            return
        refresh_books()
        select_table_book(result["accession_no"])
        record_activity(f"Borrowed book '{result['accession_no']}'")
        messagebox.showinfo(
            "Book Borrowed",
            f"Accession '{result['accession_no']}' borrowed by {result['borrower_name']}.",
        )

    def return_selected_book() -> None:
        selection = table.selection()
        if not selection:
            messagebox.showerror("No Selection", "Select a borrowed book to return.")
            return
        accession_no = str(table.item(selection[0], "values")[0])
        if not messagebox.askyesno("Confirm Return", f"Return accession '{accession_no}'?"):
            return
        try:
            result = library.return_book(accession_no)
        except ValueError as error:
            messagebox.showerror("Cannot Return Book", str(error))
            return
        except sqlite3.Error as error:
            messagebox.showerror("Database Error", f"Could not return book: {error}")
            return
        next_borrower: str | None = None
        assignment_error: str | None = None
        skipped_borrowers: list[str] = []
        while True:
            queued_request = next(
                (
                    request
                    for request in borrow_queue.to_list()
                    if request["accession_no"] == accession_no
                ),
                None,
            )
            if queued_request is None:
                break
            answer = messagebox.askyesnocancel(
                "Confirm Next Borrower",
                (
                    f"Is {queued_request['borrower_name']} available to receive "
                    f"accession '{accession_no}' now?\n\n"
                    "Yes: lend the book to them.\n"
                    "No: skip this request and ask the next person.\n"
                    "Cancel: stop and leave this request queued."
                ),
                parent=root,
            )
            if answer is None:
                break
            if not answer:
                borrow_queue.remove(queued_request)
                skipped_borrowers.append(queued_request["borrower_name"])
                record_activity(
                    f"Skipped unavailable queue request for '{accession_no}'"
                )
                continue
            try:
                next_borrowing = library.borrow_book(
                    accession_no,
                    queued_request["borrower_name"],
                )
            except ValueError as error:
                assignment_error = str(error)
            except sqlite3.Error as error:
                assignment_error = f"Database error: {error}"
            else:
                borrow_queue.remove(queued_request)
                next_borrower = next_borrowing["borrower_name"]
                record_activity(f"Borrowed queued book '{accession_no}'")
            break
        refresh_borrow_queue()
        refresh_books()
        select_table_book(result["accession_no"])
        record_activity(f"Returned book '{result['accession_no']}'")
        if next_borrower is None:
            status_message = f"Accession '{result['accession_no']}' is available again."
            if skipped_borrowers:
                status_message += (
                    "\nSkipped unavailable request(s): "
                    + ", ".join(skipped_borrowers)
                    + "."
                )
            messagebox.showinfo(
                "Book Returned",
                status_message,
            )
        else:
            status_message = (
                f"Accession '{result['accession_no']}' was returned and borrowed by "
                f"the next available person in the waiting list: {next_borrower}."
            )
            if skipped_borrowers:
                status_message += (
                    "\nSkipped unavailable request(s): "
                    + ", ".join(skipped_borrowers)
                    + "."
                )
            messagebox.showinfo(
                "Book Returned",
                status_message,
            )
        if assignment_error is not None:
            messagebox.showerror(
                "Queued Request Not Processed",
                (
                    f"The book was returned, but the queued request remains on the waiting "
                    f"list and could not be processed: {assignment_error}"
                ),
            )

    def refresh_borrow_queue() -> None:
        if (
            queue_window is None
            or queue_table is None
            or queue_empty_state is None
            or queue_filter_entry is None
            or queue_filter_field is None
            or not queue_window.winfo_exists()
        ):
            return
        for item in queue_table.get_children():
            queue_table.delete(item)
        try:
            books_by_accession = {
                book["accession_no"]: book for book in library.get_books()
            }
        except sqlite3.Error as error:
            messagebox.showerror(
                "Database Error",
                f"Could not refresh the borrow queue: {error}",
            )
            return
        requests = borrow_queue.to_list()
        query = queue_filter_entry.get().strip().casefold()
        selected_field = queue_filter_field.get()
        field_index = {
            "Position": 0,
            "Accession No.": 1,
            "Title": 2,
            "Borrower": 3,
            "Requested At": 4,
        }.get(selected_field)
        matching_requests = 0
        for position, request in enumerate(requests, start=1):
            book = books_by_accession.get(request["accession_no"])
            title = book["title"] if book else "(record unavailable)"
            display_values = (
                str(position),
                request["accession_no"],
                title,
                request["borrower_name"],
                request["requested_at"],
            )
            values_to_search = (
                display_values if field_index is None else (display_values[field_index],)
            )
            if query and not any(query in value.casefold() for value in values_to_search):
                continue
            queue_table.insert(
                "",
                tk.END,
                values=display_values,
            )
            matching_requests += 1
        if matching_requests:
            queue_empty_state.pack_forget()
        else:
            queue_empty_state.configure(
                text="No pending borrow requests."
                if not requests
                else "No requests match this filter."
            )
            queue_empty_state.pack()

    def show_borrow_queue() -> None:
        nonlocal queue_window, queue_table, queue_empty_state
        nonlocal queue_filter_entry, queue_filter_field
        if queue_window is not None and queue_window.winfo_exists():
            queue_window.lift()
            refresh_borrow_queue()
            return
        queue_window = tk.Toplevel(root)
        queue_window.title("Borrow Waiting List")
        queue_window.geometry("760x320")
        queue_window.transient(root)
        content = ttk.Frame(queue_window, padding=12)
        content.pack(fill="both", expand=True)
        ttk.Label(
            content,
            text="Borrow Waiting List (oldest request for each book is processed first)",
            font=("TkDefaultFont", 13, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        filter_bar = ttk.Frame(content)
        filter_bar.pack(fill="x", pady=(0, 8))
        ttk.Label(filter_bar, text="Filter:").pack(side="left", padx=(0, 6))
        queue_filter_field = ttk.Combobox(
            filter_bar,
            values=("All Fields", "Position", "Accession No.", "Title", "Borrower", "Requested At"),
            state="readonly",
            width=16,
        )
        queue_filter_field.set("All Fields")
        queue_filter_field.pack(side="left", padx=(0, 6))
        queue_filter_field.bind("<<ComboboxSelected>>", lambda _event: refresh_borrow_queue())
        queue_filter_entry = ttk.Entry(filter_bar)
        queue_filter_entry.pack(side="left", fill="x", expand=True)
        queue_filter_entry.bind("<KeyRelease>", lambda _event: refresh_borrow_queue())
        queue_table = ttk.Treeview(
            content,
            columns=("position", "accession_no", "title", "borrower", "requested_at"),
            show="headings",
            height=10,
        )
        queue_headings = {
            "position": "Position",
            "accession_no": "Accession No.",
            "title": "Title",
            "borrower": "Borrower",
            "requested_at": "Requested At",
        }
        queue_widths = {
            "position": 70,
            "accession_no": 110,
            "title": 230,
            "borrower": 150,
            "requested_at": 150,
        }
        for column, heading in queue_headings.items():
            queue_table.heading(column, text=heading)
            queue_table.column(column, width=queue_widths[column], anchor="w")
        queue_table.pack(fill="both", expand=True)
        queue_empty_state = ttk.Label(content, text="No pending borrow requests.")
        queue_empty_state.pack(anchor="w", pady=(6, 0))
        queue_window.protocol("WM_DELETE_WINDOW", close_borrow_queue)
        refresh_borrow_queue()

    def close_borrow_queue() -> None:
        nonlocal queue_window, queue_table, queue_empty_state
        nonlocal queue_filter_entry, queue_filter_field
        if queue_window is not None:
            queue_window.destroy()
        queue_window = None
        queue_table = None
        queue_empty_state = None
        queue_filter_entry = None
        queue_filter_field = None

    def show_recent_activity() -> None:
        window = tk.Toplevel(root)
        window.title("Recent Activity")
        window.geometry("600x300")
        window.transient(root)
        content = ttk.Frame(window, padding=12)
        content.pack(fill="both", expand=True)
        ttk.Label(content, text="Recent Activity", font=("TkDefaultFont", 13, "bold")).pack(
            anchor="w", pady=(0, 8)
        )
        if activity_stack.is_empty():
            ttk.Label(content, text="No recent activity.").pack(anchor="w")
            return

        activities = activity_entries_newest_first(activity_stack)
        ttk.Label(content, text=str(activity_stack.peek())).pack(anchor="w")
        for activity in activities[1:]:
            ttk.Label(content, text=str(activity)).pack(anchor="w")

    table.bind("<<TreeviewSelect>>", select_book)
    buttons = (
        ("Add", prepare_new_book),
        ("Save Book", save_book),
        ("Update", update_book),
        ("Delete", delete_book),
        ("Refresh", refresh_books),
        ("Borrow", borrow_selected_book),
        ("Borrow Queue", show_borrow_queue),
        ("Return", return_selected_book),
        ("Recent Activity", show_recent_activity),
    )
    for column, (text, command) in enumerate(buttons):
        button = ttk.Button(
            controls,
            text=text,
            command=command,
        )
        button.grid(row=0, column=column, padx=(0 if column == 0 else 5, 0))
        if text == "Save Book":
            save_button = button

    refresh_locator_choices()
    refresh_books()

    return root


def main() -> None:
    """Start the desktop application using the default or selected database."""
    parser = argparse.ArgumentParser(description="Run the Library Management System.")
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DEMO_DATABASE,
        help="SQLite database path (default: library_demo.db)",
    )
    args = parser.parse_args()
    create_application(args.database).mainloop()


if __name__ == "__main__":
    main()

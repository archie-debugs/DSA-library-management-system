"""Manual search and sorting algorithms for book records."""


def linear_search(records: list[dict], query: str, field: str) -> list[dict]:
    """Return records matching an accession number, title, or author query.

    Accession numbers require an exact match. Titles and authors use case-insensitive
    partial matching. The input list is never modified.
    """
    matches = []
    normalized_query = query.strip()
    if field not in ("accession_no", "title", "author"):
        raise ValueError("Search field must be accession_no, title, or author.")

    for record in records:
        value = str(record.get(field, ""))
        if field == "accession_no":
            is_match = value == normalized_query
        else:
            is_match = value.casefold().find(normalized_query.casefold()) != -1
        if is_match:
            matches.append(record)
    return matches


def insertion_sort(records: list[dict]) -> list[dict]:
    """Return a new list sorted alphabetically by title using insertion sort."""
    return insertion_sort_by(records, "title")


def insertion_sort_by(
    records: list[dict],
    field: str,
    *,
    descending: bool = False,
) -> list[dict]:
    """Return a copy of records sorted by a selected field using insertion sort."""
    numeric_fields = {"accession_no", "copyright"}

    def sort_key(record: dict) -> tuple[bool, int, int | str]:
        raw_value = record.get(field, "")
        value = "" if raw_value is None else str(raw_value).strip()
        if field in numeric_fields:
            if value.isdecimal():
                return (False, 0, int(value))
            if not value:
                return (True, 1, "")
            return (False, 1, value.casefold())
        return (False, 0, value.casefold())

    sorted_records = list(records)
    for index in range(1, len(sorted_records)):
        current = sorted_records[index]
        current_key = sort_key(current)
        position = index - 1
        while position >= 0:
            previous_key = sort_key(sorted_records[position])
            if previous_key[0] != current_key[0]:
                out_of_order = previous_key[0] and not current_key[0]
            else:
                previous_value = previous_key[1:]
                current_value = current_key[1:]
                out_of_order = (
                    previous_value < current_value
                    if descending
                    else previous_value > current_value
                )
            if not out_of_order:
                break
            sorted_records[position + 1] = sorted_records[position]
            position -= 1
        sorted_records[position + 1] = current
    return sorted_records

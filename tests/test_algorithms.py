"""Tests for the manual catalog search and insertion sort algorithms."""

import unittest

import algorithms


RECORDS = [
    {"accession_no": "1", "title": "The Hobbit", "author": "J. R. R. Tolkien"},
    {"accession_no": "2", "title": "Clean Code", "author": "Robert C. Martin"},
    {"accession_no": "3", "title": "The Clean Coder", "author": "Robert C. Martin"},
]


class AlgorithmsTestCase(unittest.TestCase):
    def test_linear_search_by_accession_title_and_author(self) -> None:
        self.assertEqual(algorithms.linear_search(RECORDS, "2", "accession_no"), [RECORDS[1]])
        self.assertEqual(algorithms.linear_search(RECORDS, "clean", "title"), RECORDS[1:])
        self.assertEqual(algorithms.linear_search(RECORDS, "MARTIN", "author"), RECORDS[1:])
        self.assertEqual(algorithms.linear_search([], "anything", "title"), [])
        self.assertEqual(algorithms.linear_search(RECORDS, "missing", "title"), [])

    def test_search_does_not_modify_input(self) -> None:
        original = list(RECORDS)
        algorithms.linear_search(RECORDS, "clean", "title")
        self.assertEqual(RECORDS, original)

    def test_insertion_sort_is_case_insensitive_and_non_mutating(self) -> None:
        records = [{"title": "b"}, {"title": "A"}, {"title": "same", "x": 1}, {"title": "SAME", "x": 2}]
        result = algorithms.insertion_sort(records)
        self.assertEqual([record["title"] for record in result], ["A", "b", "same", "SAME"])
        self.assertEqual(records, [{"title": "b"}, {"title": "A"}, {"title": "same", "x": 1}, {"title": "SAME", "x": 2}])
        self.assertEqual(algorithms.insertion_sort([]), [])

    def test_insertion_sort_by_selected_field_and_direction(self) -> None:
        records = [
            {"accession_no": "10", "author": "zoe", "copyright": "2001"},
            {"accession_no": "2", "author": "Alice", "copyright": "2024"},
            {"accession_no": "3", "author": "mike", "copyright": ""},
        ]

        ascending_accessions = algorithms.insertion_sort_by(records, "accession_no")
        descending_authors = algorithms.insertion_sort_by(
            records,
            "author",
            descending=True,
        )
        ascending_years = algorithms.insertion_sort_by(records, "copyright")
        descending_years = algorithms.insertion_sort_by(
            records,
            "copyright",
            descending=True,
        )

        self.assertEqual(
            [record["accession_no"] for record in ascending_accessions],
            ["2", "3", "10"],
        )
        self.assertEqual(
            [record["author"] for record in descending_authors],
            ["zoe", "mike", "Alice"],
        )
        self.assertEqual(
            [record["copyright"] for record in ascending_years],
            ["2001", "2024", ""],
        )
        self.assertEqual(
            [record["copyright"] for record in descending_years],
            ["2024", "2001", ""],
        )
        self.assertEqual(records[0]["accession_no"], "10")


if __name__ == "__main__":
    unittest.main()

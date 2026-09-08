import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from md_changer.core import allocate_output_path, discover_markdown_files


class DiscoverMarkdownFilesTests(unittest.TestCase):
    def test_sorts_case_fold_ties_by_original_resolved_path(self) -> None:
        class ResolvedPath:
            def __init__(self, value: str) -> None:
                self.value = value

            def __str__(self) -> str:
                return self.value

            def __hash__(self) -> int:
                return hash(self.value)

            def __eq__(self, other: object) -> bool:
                return isinstance(other, ResolvedPath) and self.value == other.value

        class Candidate:
            suffix = ".md"

            def __init__(self, value: str) -> None:
                self.resolved = ResolvedPath(value)

            def is_file(self) -> bool:
                return True

            def resolve(self) -> ResolvedPath:
                return self.resolved

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            directory = Path(temporary_directory)
            lower = Candidate("C:/docs/a.md")
            upper = Candidate("C:/docs/A.md")

            with patch.object(Path, "rglob", return_value=[lower, upper]):
                actual = discover_markdown_files([str(directory)])

            self.assertEqual(actual, [upper.resolved, lower.resolved])

    def test_accepts_only_existing_markdown_suffixes_case_insensitively(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            directory = Path(temporary_directory)
            markdown = directory / "guide.MD"
            markdown_long = directory / "readme.mArKdOwN"
            unsupported = directory / "notes.txt"
            for path in (markdown, markdown_long, unsupported):
                path.write_text(path.name, encoding="utf-8")

            actual = discover_markdown_files(
                [str(markdown), str(markdown_long), str(unsupported), str(directory / "missing.md")]
            )

            self.assertEqual(actual, [markdown.resolve(), markdown_long.resolve()])

    def test_deduplicates_duplicate_explicit_file_inputs(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            markdown = Path(temporary_directory) / "notes.md"
            markdown.write_text("# Notes", encoding="utf-8")

            actual = discover_markdown_files([str(markdown), str(markdown.resolve())])

            self.assertEqual(actual, [markdown.resolve()])

    def test_preserves_first_explicit_file_when_directory_also_contains_it(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            directory = Path(temporary_directory)
            markdown = directory / "notes.md"
            other = directory / "other.md"
            markdown.write_text("# Notes", encoding="utf-8")
            other.write_text("# Other", encoding="utf-8")

            actual = discover_markdown_files([str(markdown), str(directory)])

            self.assertEqual(actual, [markdown.resolve(), other.resolve()])

    def test_deduplicates_overlapping_directories_in_first_input_order(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            directory = Path(temporary_directory)
            nested = directory / "nested"
            nested.mkdir()
            root_file = directory / "root.md"
            nested_file = nested / "child.md"
            root_file.write_text("# Root", encoding="utf-8")
            nested_file.write_text("# Child", encoding="utf-8")

            actual = discover_markdown_files([str(nested), str(directory)])

            self.assertEqual(actual, [nested_file.resolve(), root_file.resolve()])

    def test_sorts_directory_results_by_case_insensitive_path(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            directory = Path(temporary_directory)
            nested = directory / "beta"
            nested.mkdir()
            paths = [directory / "Zoo.md", directory / "alpha.MARKDOWN", nested / "Apple.md"]
            for path in paths:
                path.write_text("# File", encoding="utf-8")

            actual = discover_markdown_files([str(directory)])

            self.assertEqual(actual, [
                (directory / "alpha.MARKDOWN").resolve(),
                (nested / "Apple.md").resolve(),
                (directory / "Zoo.md").resolve(),
            ])


class AllocateOutputPathTests(unittest.TestCase):
    def test_uses_lowest_available_suffix_for_existing_output_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            directory = Path(temporary_directory)
            input_file = directory / "report.md"
            input_file.write_text("# Report", encoding="utf-8")
            (directory / "report.pdf").write_bytes(b"existing")
            (directory / "report-2.pdf").write_bytes(b"existing")

            actual = allocate_output_path(input_file, directory)

            self.assertEqual(actual, (directory / "report-3.pdf").resolve())

    def test_skips_paths_reserved_by_current_batch(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            directory = Path(temporary_directory)
            input_file = directory / "report.md"
            input_file.write_text("# Report", encoding="utf-8")
            reserved = {(directory / "report.pdf").resolve(), (directory / "report-2.pdf").resolve()}

            actual = allocate_output_path(input_file, directory, reserved)

            self.assertEqual(actual, (directory / "report-3.pdf").resolve())


if __name__ == "__main__":
    unittest.main()

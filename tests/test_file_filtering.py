import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from md_changer import filter_new_markdown_files


class FilterNewMarkdownFilesTests(unittest.TestCase):
    def test_accepts_markdown_extensions_only(self) -> None:
        new_files, skipped = filter_new_markdown_files(
            ["a.md", "b.markdown", "c.txt"], existing_files=[]
        )

        self.assertEqual([Path("a.md"), Path("b.markdown")], new_files)
        self.assertEqual(1, skipped)

    def test_extension_check_is_case_insensitive(self) -> None:
        new_files, skipped = filter_new_markdown_files(["A.MD"], existing_files=[])

        self.assertEqual([Path("A.MD")], new_files)
        self.assertEqual(0, skipped)

    def test_skips_duplicates_within_the_same_batch(self) -> None:
        new_files, skipped = filter_new_markdown_files(["a.md", "a.md"], existing_files=[])

        self.assertEqual([Path("a.md")], new_files)
        self.assertEqual(1, skipped)

    def test_skips_files_already_in_existing_list(self) -> None:
        new_files, skipped = filter_new_markdown_files(
            ["a.md", "b.md"], existing_files=[Path("a.md")]
        )

        self.assertEqual([Path("b.md")], new_files)
        self.assertEqual(1, skipped)

    def test_returns_empty_when_nothing_qualifies(self) -> None:
        new_files, skipped = filter_new_markdown_files(["c.txt", "d.pdf"], existing_files=[])

        self.assertEqual([], new_files)
        self.assertEqual(2, skipped)


if __name__ == "__main__":
    unittest.main()

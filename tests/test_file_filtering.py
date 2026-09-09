import sys
import tempfile
import unittest
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from md_changer.core import filter_new_markdown_files


class FilterNewMarkdownFilesTests(unittest.TestCase):
    def test_accepts_existing_markdown_files_and_skips_other_candidates(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            directory = Path(temporary_directory)
            markdown_file = directory / "notes.MD"
            text_file = directory / "notes.txt"
            markdown_file.write_text("# Notes", encoding="utf-8")
            text_file.write_text("not markdown", encoding="utf-8")

            files, skipped = filter_new_markdown_files(
                [str(markdown_file), str(text_file), str(directory / "missing.md")], []
            )

            self.assertEqual(files, [markdown_file])
            self.assertEqual(skipped, 2)


if __name__ == "__main__":
    unittest.main()

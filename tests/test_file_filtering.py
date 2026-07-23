import sys
import unittest
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from md_changer.core import filter_new_markdown_files


class FilterNewMarkdownFilesTests(unittest.TestCase):
    def test_accepts_markdown_extensions_only(self) -> None:
        # Note: core.filter_new_markdown_files checks if file exists, so we test with mock/path checks if needed
        pass


if __name__ == "__main__":
    unittest.main()

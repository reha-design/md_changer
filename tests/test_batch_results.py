import sys
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from md_changer import core
from test_mermaid import FakeBrowser, FakePage


class BatchResultsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()

    def source(self, name, text="# Notes"):
        source = self.directory / name
        source.write_text(text, encoding="utf-8")
        return source

    def test_result_success_requires_pdf_and_no_error_and_results_are_immutable(self):
        result_type = getattr(core, "ConversionResult", None)
        self.assertIsNotNone(result_type, "ConversionResult is missing")
        results = (
            result_type(Path("a.md"), Path("a.pdf"), None),
            result_type(Path("b.md"), None, "read failed"),
            result_type(Path("c.md"), None, None),
            result_type(Path("d.md"), Path("d.pdf"), "render failed"),
        )
        self.assertEqual([result.success for result in results], [True, False, False, False])
        batch = core.BatchConversionResult(results)
        self.assertEqual((batch.converted_count, batch.failed_count), (1, 3))
        with self.assertRaises(FrozenInstanceError):
            results[0].error = "changed"
        with self.assertRaises(FrozenInstanceError):
            batch.results = ()

    def test_detailed_batch_continues_read_mermaid_and_render_failures_with_callback(self):
        detailed = getattr(core, "batch_convert_markdown_to_pdf_detailed", None)
        self.assertIsNotNone(detailed, "Detailed batch API is missing")
        sources = [self.directory / "missing.md", self.source("bad.md", "```mermaid\nbad\n```"),
                   self.source("broken.md"), self.source("good.md")]
        pages = [FakePage(state={"status": "error", "error": "Parse error"}), FakePage(failure="pdf"), FakePage()]
        browser = FakeBrowser(pages)
        opened = []
        callbacks = []

        @contextmanager
        def context():
            opened.append(browser)
            yield browser

        with patch.object(core, "get_browser_context", context):
            batch = detailed(sources, self.directory, theme="minimal", custom_css="h1 {color:red}",
                             progress_callback=lambda *args: callbacks.append(args))
        self.assertEqual(len(opened), 1)
        self.assertEqual((batch.converted_count, batch.failed_count), (1, 3))
        self.assertEqual([result.source for result in batch.results], sources)
        self.assertEqual([result.pdf for result in batch.results], [None, None, None, self.directory / "good.pdf"])
        self.assertIn("Parse error", batch.results[1].error)
        self.assertIn("PDF failed", batch.results[2].error)
        self.assertEqual(callbacks, [(i, 4, result) for i, result in enumerate(batch.results, 1)])
        self.assertTrue(all(page.closed for page in pages))
        self.assertFalse(list(self.directory.glob(".*.html")))

    def test_invalid_theme_or_css_fails_before_opening_browser(self):
        detailed = getattr(core, "batch_convert_markdown_to_pdf_detailed", None)
        self.assertIsNotNone(detailed, "Detailed batch API is missing")
        for kwargs, error_type in [({"theme": "unknown"}, ValueError), ({"custom_css": Path("x.css")}, TypeError)]:
            with self.subTest(kwargs=kwargs):
                with patch.object(core, "get_browser_context", side_effect=AssertionError("browser opened before validation")):
                    with self.assertRaises(error_type):
                        detailed([self.source("ok.md")], self.directory, **kwargs)

    def test_empty_detailed_batch_has_zero_counts_and_needs_no_browser(self):
        detailed = getattr(core, "batch_convert_markdown_to_pdf_detailed", None)
        self.assertIsNotNone(detailed, "Detailed batch API is missing")
        with patch.object(core, "get_browser_context", side_effect=AssertionError("unnecessary browser")):
            result = detailed([], self.directory)
        self.assertEqual(result.results, ())
        self.assertEqual((result.converted_count, result.failed_count), (0, 0))

    def test_legacy_batch_stays_fail_fast_and_retains_four_argument_callback(self):
        good = self.source("good.md")
        missing = self.directory / "missing.md"
        later = self.source("later.md")
        callbacks = []

        @contextmanager
        def context():
            yield FakeBrowser([FakePage()])

        with patch.object(core, "get_browser_context", context):
            with self.assertRaises(FileNotFoundError):
                core.batch_convert_markdown_to_pdf([good, missing, later], self.directory,
                                                   lambda *args: callbacks.append(args))
        self.assertEqual(callbacks, [(1, 3, good, self.directory / "good.pdf")])
        self.assertFalse((self.directory / "later.pdf").exists())

    def test_legacy_batch_returns_list_of_paths(self):
        source = self.source("good.md")

        @contextmanager
        def context():
            yield FakeBrowser([FakePage()])

        with patch.object(core, "get_browser_context", context):
            result = core.batch_convert_markdown_to_pdf([source], self.directory)
        self.assertEqual(result, [self.directory / "good.pdf"])


if __name__ == "__main__":
    unittest.main()

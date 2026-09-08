import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from md_changer.core import build_html, convert_markdown_to_pdf
from md_changer.styles import PDF_CSS
from md_changer.themes import compose_css, get_theme, list_themes


class ThemeRegistryTests(unittest.TestCase):
    def test_lists_built_in_themes_in_stable_order_with_korean_labels(self) -> None:
        themes = list_themes()

        self.assertEqual(
            [(theme.name, theme.label) for theme in themes],
            [
                ("default", "기본"),
                ("modern", "모던"),
                ("minimal", "미니멀"),
                ("report", "문서/리포트"),
            ],
        )
        self.assertEqual(get_theme("modern").mermaid_theme, "base")
        self.assertEqual(get_theme("minimal").mermaid_theme, "neutral")

    def test_rejects_unknown_theme_with_invalid_and_valid_names(self) -> None:
        with self.assertRaisesRegex(
            ValueError, r"unknown.*default.*modern.*minimal.*report"
        ):
            get_theme("unknown")

    def test_built_in_mermaid_variables_cannot_mutate_the_shared_registry(self) -> None:
        variables = get_theme("modern").mermaid_variables

        with self.assertRaises(TypeError):
            variables["primaryColor"] = "#000000"

        self.assertEqual(get_theme("modern").mermaid_variables["primaryColor"], "#dbeafe")

    def test_default_html_retains_the_existing_print_baseline(self) -> None:
        html = build_html("# Title", Path("document.md"))

        self.assertIn(PDF_CSS.strip(), html)
        self.assertIn("<h1 id=\"title\">Title</h1>", html)

    def test_composes_common_theme_and_custom_layers_in_precedence_order(self) -> None:
        css = compose_css("modern", "body { color: custom; }")

        common = css.index("/* md-changer: common print CSS */")
        theme = css.index("/* md-changer: theme modern */")
        custom = css.index("/* md-changer: custom CSS */")
        self.assertLess(common, theme)
        self.assertLess(theme, custom)
        self.assertTrue(css.rstrip().endswith("body { color: custom; }"))


class ConversionThemeTests(unittest.TestCase):
    def test_conversion_passes_theme_and_custom_css_into_rendered_html(self) -> None:
        class CapturingPage:
            def __init__(self) -> None:
                self.html = ""

            def goto(self, uri: str, **_kwargs: object) -> None:
                self.html = Path(uri.removeprefix("file:///" )).read_text(encoding="utf-8")

            def pdf(self, *, path: str, **_kwargs: object) -> None:
                Path(path).write_bytes(b"pdf")

            def evaluate(self, _expression: str) -> None:
                pass

            def close(self) -> None:
                pass

        class CapturingBrowser:
            def __init__(self) -> None:
                self.page = CapturingPage()

            def new_page(self, **_kwargs: object) -> CapturingPage:
                return self.page

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary_directory:
            directory = Path(temporary_directory)
            source = directory / "notes.md"
            source.write_text("# Notes", encoding="utf-8")
            browser = CapturingBrowser()

            output = convert_markdown_to_pdf(
                source,
                directory,
                browser=browser,
                theme="report",
                custom_css="h1 { color: #123456; }",
            )

            self.assertTrue(output.exists())
            self.assertIn("/* md-changer: theme report */", browser.page.html)
            self.assertLess(
                browser.page.html.index("/* md-changer: theme report */"),
                browser.page.html.index("h1 { color: #123456; }"),
            )
            self.assertIn("h1 { color: #123456; }\n</style>", browser.page.html)


if __name__ == "__main__":
    unittest.main()

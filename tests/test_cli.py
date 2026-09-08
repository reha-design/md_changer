import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import ANY, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from md_changer import cli
from md_changer.core import BatchConversionResult, ConversionResult


class CliIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.source = self.directory / "notes.md"
        self.source.write_text("# Notes", encoding="utf-8")
        self.output = self.directory / "notes.pdf"

    def run_main(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = cli.main(args)
            except SystemExit as exit_error:
                code = exit_error.code
            except OSError:
                code = -1
        return code, stdout.getvalue(), stderr.getvalue()

    def test_defaults_to_default_theme_and_no_custom_css(self) -> None:
        parsed = cli.parse_args(["--input", str(self.source)])

        self.assertEqual(getattr(parsed, "theme", None), "default")
        self.assertIsNone(getattr(parsed, "css", None))

    def test_theme_accepts_only_registered_names(self) -> None:
        parsed = cli.parse_args(["--input", str(self.source), "--theme", "report"])
        self.assertEqual(parsed.theme, "report")

        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as exit_context:
                cli.parse_args(["--input", str(self.source), "--theme", "unlisted"])
        self.assertEqual(exit_context.exception.code, 2)

    def test_css_preflight_rejects_missing_directories_and_non_utf8_files_before_batch(self) -> None:
        invalid_paths = [
            self.directory / "missing.css",
            self.directory,
            self.directory / "invalid.css",
        ]
        invalid_paths[-1].write_bytes(b"\x80")

        for css_path in invalid_paths:
            with self.subTest(css_path=css_path), patch.object(
                cli, "batch_convert_markdown_to_pdf_detailed", create=True
            ) as detailed:
                code, stdout, stderr = self.run_main(
                    ["--input", str(self.source), "--css", str(css_path), "--json"]
                )

                self.assertEqual(code, 1)
                self.assertEqual(stderr.count("Error:"), 1)
                self.assertEqual(json.loads(stdout)["status"], "error")
                detailed.assert_not_called()

    def test_json_invalid_theme_returns_one_error_document(self) -> None:
        code, stdout, _stderr = self.run_main(
            ["--json", "--input", str(self.source), "--theme", "invalid"]
        )

        self.assertEqual(code, 1)
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "error")
        self.assertIn("invalid choice", payload["message"])

    def test_json_missing_input_returns_one_error_document(self) -> None:
        code, stdout, _stderr = self.run_main(["--json"])

        self.assertEqual(code, 1)
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "error")
        self.assertIn("required", payload["message"])

    def test_json_discovery_exception_returns_one_error_document(self) -> None:
        with patch.object(cli, "discover_markdown_files", side_effect=OSError("input scan failed")):
            code, stdout, _stderr = self.run_main(["--json", "--input", str(self.source)])

        self.assertEqual(code, 1)
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["message"], "input scan failed")

    def test_success_json_has_complete_schema_and_exit_zero(self) -> None:
        css_path = self.directory / "custom.css"
        css_path.write_text("h1 { color: navy; }", encoding="utf-8")
        batch = BatchConversionResult(
            (ConversionResult(self.source, self.output, None),)
        )
        with patch.object(cli, "batch_convert_markdown_to_pdf_detailed", create=True, return_value=batch) as detailed:
            code, stdout, stderr = self.run_main(
                ["--input", str(self.source), "--theme", "modern", "--css", str(css_path), "--json"]
            )

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(
            payload,
            {
                "status": "success",
                "converted_count": 1,
                "failed_count": 0,
                "output_directory": str(self.directory),
                "theme": "modern",
                "custom_css": str(css_path),
                "files": [
                    {
                        "source": str(self.source),
                        "pdf": str(self.output),
                        "status": "success",
                        "error": None,
                    }
                ],
            },
        )
        detailed.assert_called_once_with(
            [self.source], self.directory, theme="modern", custom_css="h1 { color: navy; }", progress_callback=ANY
        )

    def test_partial_json_marks_failed_file_and_exits_one(self) -> None:
        failed_source = self.directory / "broken.md"
        batch = BatchConversionResult(
            (
                ConversionResult(self.source, self.output, None),
                ConversionResult(failed_source, None, "render failed"),
            )
        )
        with patch.object(cli, "batch_convert_markdown_to_pdf_detailed", create=True, return_value=batch):
            code, stdout, stderr = self.run_main(["--input", str(self.source), "--json"])

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "partial")
        self.assertEqual((payload["converted_count"], payload["failed_count"]), (1, 1))
        self.assertEqual(
            payload["files"][1],
            {
                "source": str(failed_source),
                "pdf": None,
                "status": "error",
                "error": "render failed",
            },
        )

    def test_total_error_json_and_quiet_mode_still_report_errors_to_stderr(self) -> None:
        batch = BatchConversionResult(
            (ConversionResult(self.source, None, "could not render"),)
        )
        with patch.object(cli, "batch_convert_markdown_to_pdf_detailed", create=True, return_value=batch):
            code, stdout, stderr = self.run_main(
                ["--input", str(self.source), "--quiet", "--json"]
            )

        self.assertEqual(code, 1)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual((payload["converted_count"], payload["failed_count"]), (0, 1))
        self.assertEqual(payload["files"][0]["pdf"], None)
        self.assertEqual(payload["files"][0]["error"], "could not render")

        code, stdout, stderr = self.run_main(
            ["--input", str(self.source), "--css", str(self.directory / "missing.css"), "--quiet"]
        )
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Error:", stderr)


if __name__ == "__main__":
    unittest.main()

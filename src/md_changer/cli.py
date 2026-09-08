"""CLI entry point for md_changer."""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from md_changer.core import (
    BatchConversionResult,
    ConversionResult,
    batch_convert_markdown_to_pdf_detailed,
    discover_markdown_files,
)


THEME_CHOICES = ("default", "modern", "minimal", "report")


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="md-changer",
        description="Convert Markdown files to PDF using Playwright Chromium.",
    )
    parser.add_argument(
        "-i", "--input", nargs="+", required=True,
        help="One or more input Markdown file paths or directory paths.",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output directory path for generated PDFs. (Default: current directory or input directory)",
    )
    parser.add_argument(
        "--theme", choices=THEME_CHOICES, default="default",
        help="Built-in document theme. (Default: default)",
    )
    parser.add_argument(
        "--css", default=None, metavar="PATH",
        help="Optional UTF-8 CSS file applied after the selected theme.",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="Suppress output messages except errors.",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output execution results formatted as a JSON object.",
    )
    return parser.parse_args(args)


def _resolve_custom_css(raw_path: str | None) -> tuple[Path | None, str | None]:
    """Resolve and read user CSS before the renderer is initialized."""
    if raw_path is None:
        return None, None

    css_path = Path(raw_path).expanduser().resolve()
    if not css_path.is_file():
        raise ValueError(f"CSS path must be an existing file: {css_path}")
    try:
        return css_path, css_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Unable to read CSS file as UTF-8: {css_path}: {error}") from error


def _file_payload(result: ConversionResult) -> dict[str, str | None]:
    return {
        "source": str(result.source),
        "pdf": str(result.pdf) if result.pdf is not None else None,
        "status": "success" if result.success else "error",
        "error": None if result.success else result.error,
    }


def _json_payload(
    *,
    status: str,
    output_folder: Path | None,
    theme: str,
    css_path: Path | None,
    batch: BatchConversionResult | None = None,
    message: str | None = None,
) -> dict[str, object]:
    results = batch.results if batch is not None else ()
    payload: dict[str, object] = {
        "status": status,
        "converted_count": batch.converted_count if batch is not None else 0,
        "failed_count": batch.failed_count if batch is not None else 0,
        "output_directory": str(output_folder) if output_folder is not None else None,
        "theme": theme,
        "custom_css": str(css_path) if css_path is not None else None,
        "files": [_file_payload(result) for result in results],
    }
    if message is not None:
        payload["message"] = message
    return payload


def _batch_status(batch: BatchConversionResult) -> str:
    if batch.converted_count == len(batch.results) and batch.converted_count > 0:
        return "success"
    if batch.converted_count > 0:
        return "partial"
    return "error"


def _print_error(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)


def _argument_error_message(parser_output: str) -> str:
    """Extract argparse's actionable error line without its usage banner."""
    for line in reversed(parser_output.splitlines()):
        if ": error: " in line:
            return line.split(": error: ", 1)[1]
    return "Unable to parse command-line arguments."


def _parse_json_args(raw_args: list[str]) -> tuple[argparse.Namespace | None, str | None]:
    """Parse JSON-mode arguments without allowing argparse to write output."""
    parser_stdout = io.StringIO()
    parser_stderr = io.StringIO()
    with redirect_stdout(parser_stdout), redirect_stderr(parser_stderr):
        try:
            return parse_args(raw_args), None
        except SystemExit:
            message = _argument_error_message(parser_stderr.getvalue())
            if message == "Unable to parse command-line arguments.":
                message = "Argument parsing ended before conversion could begin."
            return None, message


def _emit_json_error(
    message: str,
    *,
    output_folder: Path | None = None,
    theme: str = "default",
    css_path: Path | None = None,
) -> None:
    print(
        json.dumps(
            _json_payload(
                status="error",
                output_folder=output_folder,
                theme=theme,
                css_path=css_path,
                message=message,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


def main(args: list[str] | None = None) -> int:
    raw_args = list(args) if args is not None else sys.argv[1:]
    json_requested = "--json" in raw_args
    if json_requested:
        parsed_args, parse_error = _parse_json_args(raw_args)
        if parse_error is not None:
            _emit_json_error(parse_error)
            return 1
        assert parsed_args is not None
    else:
        parsed_args = parse_args(raw_args)

    output_folder: Path | None = None
    css_path: Path | None = None

    try:
        input_paths = discover_markdown_files(parsed_args.input)
        css_path = Path(parsed_args.css).expanduser().resolve() if parsed_args.css else None
        if input_paths:
            output_folder = (
                Path(parsed_args.output).resolve()
                if parsed_args.output
                else input_paths[0].parent.resolve()
            )
        elif parsed_args.output:
            output_folder = Path(parsed_args.output).resolve()

        resolved_css_path, custom_css = _resolve_custom_css(parsed_args.css)
        css_path = resolved_css_path

        if not input_paths:
            raise ValueError("No valid Markdown files found for conversion.")

        assert output_folder is not None
        output_folder.mkdir(parents=True, exist_ok=True)

        if not parsed_args.quiet and not parsed_args.json:
            for item in parsed_args.input:
                path = Path(item)
                if not path.is_file() and not path.is_dir():
                    print(f"Warning: Skipped invalid or non-markdown input: {item}", file=sys.stderr)
            print(f"Found {len(input_paths)} file(s) to convert to PDF.")
            print(f"Output Directory: {output_folder}")

        def progress_callback(current: int, total: int, result: ConversionResult) -> None:
            if result.success:
                if not parsed_args.quiet and not parsed_args.json:
                    print(f"[{current}/{total}] Converted '{result.source.name}' -> '{result.pdf}'")
            elif not parsed_args.json:
                _print_error(f"Failed '{result.source.name}': {result.error}")

        batch = batch_convert_markdown_to_pdf_detailed(
            input_paths,
            output_folder,
            theme=parsed_args.theme,
            custom_css=custom_css,
            progress_callback=progress_callback,
        )
    except Exception as error:
        if parsed_args.json:
            _emit_json_error(
                str(error) or type(error).__name__,
                output_folder=output_folder,
                theme=parsed_args.theme,
                css_path=css_path,
            )
        _print_error(str(error) or type(error).__name__)
        return 1

    status = _batch_status(batch)
    if parsed_args.json:
        print(
            json.dumps(
                _json_payload(
                    status=status,
                    output_folder=output_folder,
                    theme=parsed_args.theme,
                    css_path=css_path,
                    batch=batch,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        if not parsed_args.quiet:
            print(
                f"Conversion finished: {batch.converted_count} succeeded, "
                f"{batch.failed_count} failed."
            )

    return 0 if status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())

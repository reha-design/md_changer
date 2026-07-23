"""CLI Entry Point for md_changer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from md_changer.core import MARKDOWN_SUFFIXES, batch_convert_markdown_to_pdf


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="md-changer",
        description="Convert Markdown files to PDF using Playwright Chromium.",
    )
    parser.add_argument(
        "-i",
        "--input",
        nargs="+",
        required=True,
        help="One or more input Markdown file paths or directory paths.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output directory path for generated PDFs. (Default: current directory or input directory)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress output messages except errors.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output execution results formatted as a JSON object.",
    )
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    parsed_args = parse_args(args)

    input_paths: list[Path] = []
    for item in parsed_args.input:
        path = Path(item)
        if path.is_file() and path.suffix.lower() in MARKDOWN_SUFFIXES:
            input_paths.append(path)
        elif path.is_dir():
            for ext in MARKDOWN_SUFFIXES:
                input_paths.extend(path.glob(f"*{ext}"))
                input_paths.extend(path.glob(f"**/*{ext}"))
        else:
            if not parsed_args.quiet and not parsed_args.json:
                print(f"Warning: Skipped invalid or non-markdown input: {item}", file=sys.stderr)

    if not input_paths:
        if parsed_args.json:
            import json
            print(json.dumps({"status": "error", "message": "No valid Markdown files found for conversion."}))
        else:
            print("Error: No valid Markdown files found for conversion.", file=sys.stderr)
        return 1

    output_folder = (
        Path(parsed_args.output).resolve()
        if parsed_args.output
        else (input_paths[0].parent.resolve() if input_paths[0].parent.exists() else Path.cwd())
    )

    output_folder.mkdir(parents=True, exist_ok=True)

    if not parsed_args.quiet and not parsed_args.json:
        print(f"Found {len(input_paths)} file(s) to convert to PDF.")
        print(f"Output Directory: {output_folder}")

    def progress_callback(current: int, total: int, src: Path, dist: Path):
        if not parsed_args.quiet and not parsed_args.json:
            print(f"[{current}/{total}] Converted '{src.name}' -> '{dist}'")

    try:
        generated = batch_convert_markdown_to_pdf(
            input_paths, output_folder, progress_callback=progress_callback
        )
        if parsed_args.json:
            import json
            result_data = {
                "status": "success",
                "converted_count": len(generated),
                "output_directory": str(output_folder),
                "files": [
                    {
                        "source": str(src),
                        "pdf": str(dist)
                    }
                    for src, dist in zip(input_paths, generated)
                ]
            }
            print(json.dumps(result_data, ensure_ascii=False, indent=2))
        elif not parsed_args.quiet:
            print(f"Successfully converted {len(generated)} file(s).")
        return 0
    except Exception as e:
        if parsed_args.json:
            import json
            print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        else:
            print(f"Error during conversion: {e}", file=sys.stderr)
        return 1



if __name__ == "__main__":
    sys.exit(main())

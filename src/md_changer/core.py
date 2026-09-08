"""Core Markdown to PDF conversion engine using Playwright."""

from __future__ import annotations

import html
import json
import os
import re
import sys
import uuid
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import markdown
from playwright.sync_api import Browser, TimeoutError as PlaywrightTimeoutError, sync_playwright

from md_changer.themes import compose_css, get_theme

APP_NAME = "Markdown PDF 변환기"
MARKDOWN_SUFFIXES = {".md", ".markdown"}
MERMAID_BLOCK = re.compile(r'<pre><code class="language-mermaid">(.*?)</code></pre>', re.DOTALL)


@dataclass(frozen=True)
class ConversionResult:
    """The output or error for one source document."""

    source: Path
    pdf: Path | None
    error: str | None

    @property
    def success(self) -> bool:
        return self.error is None and self.pdf is not None


@dataclass(frozen=True)
class BatchConversionResult:
    """Ordered conversion outcomes, including individual failures."""

    results: tuple[ConversionResult, ...]

    @property
    def converted_count(self) -> int:
        return sum(result.success for result in self.results)

    @property
    def failed_count(self) -> int:
        return len(self.results) - self.converted_count


def _prepare_mermaid(body: str, theme: str) -> tuple[str, str]:
    """Prepare only Mermaid code fences, keeping source inert until textContent."""
    def replace(match: re.Match[str]) -> str:
        source = html.escape(html.unescape(match.group(1)), quote=True)
        return f'<div class="mermaid" data-md-changer-source="{source}"></div>'

    body, count = MERMAID_BLOCK.subn(replace, body)
    if not count:
        return body, ""

    definition = get_theme(theme)
    config = json.dumps({
        "startOnLoad": False,
        "securityLevel": "strict",
        "suppressErrorRendering": True,
        "theme": definition.mermaid_theme,
        "themeVariables": dict(definition.mermaid_variables),
    })
    runtime = Path(__file__).resolve().parent / "assets" / "mermaid.min.js"
    scripts = f"""<script src="{runtime.as_uri()}"></script>
<script>
window.__mdChangerMermaid = {{status: "pending", error: null}};
(async () => {{
  try {{
    const nodes = document.querySelectorAll(".mermaid[data-md-changer-source]");
    for (const node of nodes) {{
      node.textContent = node.dataset.mdChangerSource;
      node.removeAttribute("data-md-changer-source");
    }}
    mermaid.initialize({config});
    await document.fonts.ready;
    await mermaid.run({{nodes, suppressErrors: false}});
    window.__mdChangerMermaid = {{status: "success", error: null}};
  }} catch (error) {{
    window.__mdChangerMermaid = {{status: "error", error: String(error.message || error)}};
  }}
}})();
</script>"""
    return body, scripts


def discover_markdown_files(raw_inputs: Iterable[str]) -> list[Path]:
    """Return unique, existing Markdown files from file and directory inputs."""
    discovered: list[Path] = []
    seen: set[Path] = set()

    for raw_input in raw_inputs:
        path = Path(raw_input)
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(
                (candidate for candidate in path.rglob("*") if candidate.is_file()),
                key=lambda candidate: (
                    str(candidate.resolve()).casefold(),
                    str(candidate.resolve()),
                ),
            )
        else:
            continue

        for candidate in candidates:
            if candidate.suffix.lower() not in MARKDOWN_SUFFIXES:
                continue
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                discovered.append(resolved)

    return discovered


def allocate_output_path(
    input_file: Path, output_folder: Path, reserved: set[Path] | None = None
) -> Path:
    """Find the first unused PDF path for an input Markdown file."""
    input_file = Path(input_file).resolve()
    output_folder = Path(output_folder).resolve()
    reserved_paths = {Path(path).resolve() for path in reserved or set()}

    suffix = 1
    while True:
        filename = f"{input_file.stem}.pdf" if suffix == 1 else f"{input_file.stem}-{suffix}.pdf"
        candidate = output_folder / filename
        if not candidate.exists() and candidate not in reserved_paths:
            return candidate
        suffix += 1


def resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller."""
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return Path(base_path) / relative_path
    return Path(__file__).resolve().parent.parent.parent / relative_path


def configure_playwright_browser_path() -> None:
    """Set PLAYWRIGHT_BROWSERS_PATH if bundled browser directory exists."""
    bundled_browser_dir = resource_path("ms-playwright")
    if bundled_browser_dir.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled_browser_dir)


def build_html(
    markdown_text: str,
    source_path: Path,
    custom_css: str | None = None,
    *,
    theme: str = "default",
) -> str:
    """Convert markdown text to styled HTML document."""
    document, _has_mermaid = _build_html_document(
        markdown_text, source_path, custom_css, theme=theme
    )
    return document


def _build_html_document(
    markdown_text: str,
    source_path: Path,
    custom_css: str | None = None,
    *,
    theme: str = "default",
) -> tuple[str, bool]:
    """Return HTML and whether fenced diagrams require a completion wait."""
    body = markdown.markdown(
        markdown_text,
        extensions=[
            "extra",
            "sane_lists",
            "smarty",
            "toc",
        ],
        output_format="html5",
    )
    base_uri = source_path.parent.resolve().as_uri() + "/"
    title = html.escape(source_path.stem)
    css_content = compose_css(theme, custom_css)
    body, mermaid_scripts = _prepare_mermaid(body, theme)

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <base href="{base_uri}">
  <title>{title}</title>
  <style>{css_content}</style>
</head>
<body>
{body}
{mermaid_scripts}
</body>
</html>
""", bool(mermaid_scripts)


def filter_new_markdown_files(
    raw_paths: Iterable[str], existing_files: Iterable[Path]
) -> tuple[list[Path], int]:
    """Filter candidate paths down to new, valid Markdown files.

    Returns the ordered list of files to add and a count of candidates
    skipped for having the wrong extension or already being present.
    """
    seen = {path.resolve() for path in existing_files if path.exists()}
    new_files: list[Path] = []
    skipped = 0
    for raw in raw_paths:
        path = Path(raw)
        if not path.is_file() or path.suffix.lower() not in MARKDOWN_SUFFIXES:
            skipped += 1
            continue
        resolved = path.resolve()
        if resolved in seen:
            skipped += 1
            continue
        seen.add(resolved)
        new_files.append(path)
    return new_files, skipped


@contextmanager
def get_browser_context():
    """Context manager providing a Playwright Chromium browser instance."""
    configure_playwright_browser_path()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            browser.close()


def convert_markdown_to_pdf(
    input_file: Path,
    output_folder: Path,
    browser: Browser | None = None,
    *,
    theme: str = "default",
    custom_css: str | None = None,
) -> Path:
    """Convert a single Markdown file into a PDF file using Playwright.

    If no browser instance is passed, a temporary Chromium instance is launched.
    """
    input_file = Path(input_file).resolve()
    output_folder = Path(output_folder).resolve()
    output_folder.mkdir(parents=True, exist_ok=True)

    markdown_text = input_file.read_text(encoding="utf-8")
    output_file = allocate_output_path(input_file, output_folder)
    html_text, has_mermaid = _build_html_document(
        markdown_text, input_file, custom_css, theme=theme
    )

    html_file = output_folder / f".{input_file.stem}.md_changer_{uuid.uuid4().hex}.html"

    def _render_with_browser(b: Browser) -> Path:
        page = b.new_page(offline=True)
        try:
            page.goto(html_file.resolve().as_uri(), wait_until="networkidle", timeout=30000)
            if has_mermaid:
                try:
                    page.wait_for_function(
                        "window.__mdChangerMermaid && window.__mdChangerMermaid.status !== 'pending'",
                        timeout=30000,
                    )
                except PlaywrightTimeoutError as error:
                    raise RuntimeError("Mermaid rendering timed out after 30 seconds") from error
                state = page.evaluate("window.__mdChangerMermaid")
                if state["status"] != "success":
                    raise RuntimeError(f"Mermaid rendering failed: {state['error']}")
            page.evaluate("() => document.fonts.ready.then(() => true)")
            page.pdf(
                path=str(output_file),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
            )
        finally:
            page.close()
        return output_file

    try:
        html_file.write_text(html_text, encoding="utf-8")
        if browser is not None:
            return _render_with_browser(browser)
        else:
            with get_browser_context() as temp_browser:
                return _render_with_browser(temp_browser)
    finally:
        try:
            html_file.unlink(missing_ok=True)
        except OSError:
            pass


def batch_convert_markdown_to_pdf(
    input_files: Iterable[Path], output_folder: Path, progress_callback=None
) -> list[Path]:
    """Convert multiple Markdown files to PDF using a single browser instance."""
    input_paths = [Path(p).resolve() for p in input_files]
    output_folder = Path(output_folder).resolve()
    output_folder.mkdir(parents=True, exist_ok=True)

    generated_pdfs: list[Path] = []

    with get_browser_context() as browser:
        for idx, input_file in enumerate(input_paths, start=1):
            pdf_path = convert_markdown_to_pdf(input_file, output_folder, browser=browser)
            generated_pdfs.append(pdf_path)
            if progress_callback:
                progress_callback(idx, len(input_paths), input_file, pdf_path)

    return generated_pdfs


def batch_convert_markdown_to_pdf_detailed(
    input_files: Iterable[Path],
    output_folder: Path,
    *,
    theme: str = "default",
    custom_css: str | None = None,
    progress_callback=None,
) -> BatchConversionResult:
    """Reuse one browser and report each file's outcome without stopping the job.

    Invalid theme/CSS and browser startup errors are job-level errors. Callback
    exceptions propagate to the caller rather than being mistaken for file errors.
    """
    compose_css(theme, custom_css)
    input_paths = [Path(path).resolve() for path in input_files]
    if not input_paths:
        return BatchConversionResult(())
    output_folder = Path(output_folder).resolve()
    output_folder.mkdir(parents=True, exist_ok=True)
    results: list[ConversionResult] = []
    with get_browser_context() as browser:
        for index, source in enumerate(input_paths, start=1):
            try:
                pdf = convert_markdown_to_pdf(
                    source, output_folder, browser=browser, theme=theme, custom_css=custom_css
                )
            except Exception as error:
                result = ConversionResult(source, None, str(error) or type(error).__name__)
            else:
                result = ConversionResult(source, pdf, None)
            results.append(result)
            if progress_callback is not None:
                progress_callback(index, len(input_paths), result)
    return BatchConversionResult(tuple(results))

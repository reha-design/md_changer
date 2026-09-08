# Markdown Themes and Mermaid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe batch conversion, four layered document themes, optional user CSS, offline Mermaid rendering, GUI/CLI integration, packaging, and documentation while preserving existing Python APIs.

**Architecture:** Keep Playwright Chromium as the single renderer. Add a focused theme registry and structured batch result types in the core package; both GUI and CLI consume the same detailed batch API while the existing batch function remains a fail-fast compatibility wrapper. Bundle Mermaid 11.17.2 locally and render fenced Mermaid blocks to SVG before PDF generation.

**Tech Stack:** Python 3.13+, Python-Markdown, Playwright Chromium, TkinterDnD2, unittest, PyInstaller, bundled Mermaid 11.17.2.

**Spec:** User-approved plan in the Codex conversation on 2026-09-08.

## Global Constraints

- Preserve `batch_convert_markdown_to_pdf(...) -> list[Path]` and its fail-fast exception behavior.
- Apply CSS in this exact order: common print CSS, selected built-in theme CSS, optional UTF-8 user CSS.
- Built-in theme names are exactly `default`, `modern`, `minimal`, and `report`; default is `default`.
- One theme applies to the whole conversion job; GUI preview and external theme directory discovery are out of scope.
- Never overwrite an existing output; choose the lowest available suffix (`name.pdf`, `name-2.pdf`, `name-3.pdf`).
- Detailed batches continue after per-file read, Mermaid, or rendering failures.
- Mermaid version is 11.17.2, bundled locally with its MIT license; no CDN/network dependency at render time.
- Mermaid uses `startOnLoad: false`, `securityLevel: "strict"`, and a 30-second completion timeout.
- CLI returns exit code 0 only when every file succeeds and 1 for partial or total failure.

---

### Task 1: Safe Input Discovery and Output Allocation

**Files:**
- Modify: `src/md_changer/core.py`
- Modify: `src/md_changer/cli.py`
- Replace: `tests/test_file_filtering.py`
- Create: `tests/test_paths.py`

**Interfaces:**
- Produce `discover_markdown_files(raw_inputs: Iterable[str]) -> list[Path]`, preserving argument order, sorting each directory recursively, and de-duplicating resolved paths.
- Produce `allocate_output_path(input_file: Path, output_folder: Path, reserved: set[Path] | None = None) -> Path` with lowest-available suffix behavior.

- [ ] Write real temporary-file tests for supported suffixes, invalid paths, duplicates, explicit-file/directory overlap, deterministic directory order, and output suffix allocation.
- [ ] Run focused tests and confirm failures identify missing discovery/allocation behavior.
- [ ] Implement the two helpers and route CLI discovery plus single/batch output selection through them.
- [ ] Run the focused and full unittest suites and confirm all pass.
- [ ] Commit the task.

### Task 2: Layered Theme Registry and Custom CSS

**Files:**
- Create: `src/md_changer/themes.py`
- Modify: `src/md_changer/styles.py`
- Modify: `src/md_changer/core.py`
- Create: `tests/test_themes.py`

**Interfaces:**
- Produce immutable `ThemeDefinition(name: str, label: str, css: str, mermaid_theme: str, mermaid_variables: dict[str, str])`.
- Produce `THEMES`, `list_themes()`, `get_theme(name)`, and `compose_css(theme="default", custom_css=None)`.
- Extend `build_html(..., custom_css=None, *, theme="default")` without breaking its existing third positional argument.
- Extend `convert_markdown_to_pdf(..., browser=None, *, theme="default", custom_css=None)`.

- [ ] Write tests for exact theme names, invalid names, default backward compatibility, CSS layer order, custom CSS precedence, and HTML integration.
- [ ] Run focused tests and confirm expected failures.
- [ ] Implement the theme registry, four styles, and keyword-only theme plumbing.
- [ ] Run focused and full suites and confirm all pass.
- [ ] Commit the task.

### Task 3: Detailed Batch Results and Offline Mermaid Rendering

**Files:**
- Modify: `src/md_changer/core.py`
- Create: `src/md_changer/assets/mermaid.min.js`
- Create: `src/md_changer/assets/mermaid.LICENSE.txt`
- Create: `tests/test_batch_results.py`
- Create: `tests/test_mermaid.py`

**Interfaces:**
- Produce immutable `ConversionResult(source: Path, pdf: Path | None, error: str | None)` with `success` property.
- Produce immutable `BatchConversionResult(results: tuple[ConversionResult, ...])` with `converted_count` and `failed_count` properties.
- Produce `batch_convert_markdown_to_pdf_detailed(input_files, output_folder, *, theme="default", custom_css=None, progress_callback=None) -> BatchConversionResult`; callback receives `(current, total, ConversionResult)`.
- Keep the old batch API fail-fast and returning `list[Path]`.

- [ ] Write tests for Mermaid-only block detection, normal code preservation, script injection, theme mapping, completion waiting, syntax/timeout failure, detailed partial success, callback results, and legacy batch behavior.
- [ ] Run focused tests and confirm failures are caused by missing features.
- [ ] Add the pinned Mermaid bundle/license, transform Mermaid fenced blocks, inject the local runtime only when needed, wait up to 30 seconds for success/error, and wait for fonts before PDF.
- [ ] Implement detailed results and continue-on-error while retaining the compatibility wrapper.
- [ ] Run focused and full suites and confirm all pass.
- [ ] Commit the task.

### Task 4: CLI and GUI Integration

**Files:**
- Modify: `src/md_changer/cli.py`
- Modify: `src/md_changer/gui.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Add CLI `--theme {default,modern,minimal,report}` and `--css PATH`.
- JSON retains existing fields and adds `failed_count`, `theme`, `custom_css`, and per-file `status`/`error`; failed items use `pdf: null`.
- Overall JSON status is `success`, `partial`, or `error`.

- [ ] Write CLI tests for option validation, missing/unreadable CSS, success/partial/error JSON, and exit codes.
- [ ] Run tests and confirm expected failures.
- [ ] Implement CLI preflight, detailed result output, and quiet/human-readable summaries.
- [ ] Add GUI theme selection, CSS choose/clear controls, busy-state disabling, and success/failure summary dialogs.
- [ ] Run focused and full suites and confirm all pass.
- [ ] Commit the task.

### Task 5: Packaging, Documentation, and End-to-End Verification

**Files:**
- Modify: `pyproject.toml`
- Modify: `md_changer.spec`
- Modify: `build.ps1`
- Modify: `README.md`
- Modify: `SKILL.md`
- Add or update a Mermaid sample fixture.

**Interfaces:**
- Package `assets/*.js` and `assets/*.txt` for wheel/uvx and PyInstaller.
- PyInstaller analyzes `main.py` with `src` on `pathex` and includes Mermaid assets plus Chromium.

- [ ] Add a build/test check that fails clearly when the pinned Mermaid asset is missing.
- [ ] Run it and confirm the expected failure before packaging changes.
- [ ] Update package data, PyInstaller entrypoint/data collection, and build script preflight tests.
- [ ] Document themes, CSS precedence, Mermaid examples, collision naming, detailed JSON, and Python API compatibility.
- [ ] Run the full unittest suite, a real Chromium Mermaid conversion, and the portable build; inspect the generated PDF and built asset layout.
- [ ] Commit the task.

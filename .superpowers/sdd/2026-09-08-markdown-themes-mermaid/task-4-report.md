# Task 4: CLI and GUI Integration Report

## RED

Command:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.test_cli.CliIntegrationTests.test_defaults_to_default_theme_and_no_custom_css
```

Output after correcting the test fixture location:

```text
FAIL: test_defaults_to_default_theme_and_no_custom_css
AssertionError: None != 'default'
Ran 1 test in 0.004s
FAILED (failures=1)
```

The failure showed that the CLI parser did not yet expose the required default
theme option. An earlier sandboxed run could not create its temporary fixture;
the same focused test was then run with the required filesystem permission.

## GREEN

Focused CLI suite:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.test_cli
```

```text
Ran 6 tests in 0.239s
OK
```

Syntax and full suite:

```powershell
& .\.venv\Scripts\python.exe -m py_compile src\md_changer\cli.py src\md_changer\gui.py
& .\.venv\Scripts\python.exe -m unittest discover -s tests
git diff --check
```

```text
Ran 39 tests in 3.617s
OK
```

`git diff --check` completed without whitespace errors. Git emitted only its
normal LF-to-CRLF informational warnings for the two edited source files.

## Files changed

- `src/md_changer/cli.py`
  - Adds fixed theme choices and UTF-8 CSS preflight.
  - Routes conversion through `batch_convert_markdown_to_pdf_detailed`.
  - Produces the detailed JSON result schema and correct success/partial/error
    exit statuses.
  - Preserves quiet-mode error reporting on stderr.
- `src/md_changer/gui.py`
  - Adds registry-label-backed read-only theme selection.
  - Adds optional CSS display, selection, and clearing controls.
  - Disables theme/CSS controls during conversion and reports per-file failures.
  - Routes conversion through the detailed batch API.
- `tests/test_cli.py`
  - Adds parser, CSS preflight, JSON schema, partial/total failure, quiet-mode,
    and exit-code integration coverage using the detailed batch API seam.

## Self-review

- The legacy `batch_convert_markdown_to_pdf` API was not modified.
- CLI CSS is resolved and decoded as UTF-8 before output setup or renderer use.
- JSON output always contains one document on runtime job/preflight errors and
  has null PDF/error fields in the prescribed success/failure positions.
- GUI applies one selected theme/CSS payload to the whole batch and does not add
  a preview surface.
- Per-file errors are emitted once to stderr in non-JSON CLI operation, including
  quiet mode.

## Concerns

- GUI behavior was syntax-checked and covered by the shared full suite, but this
  project has no native Tkinter interaction test harness; the controls should be
  exercised manually when doing the Task 5 end-to-end verification.

## Fix round: JSON parser errors and GUI total-failure title

### RED

Command:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.test_cli.CliIntegrationTests.test_json_invalid_theme_returns_one_error_document tests.test_cli.CliIntegrationTests.test_json_missing_input_returns_one_error_document tests.test_cli.CliIntegrationTests.test_json_discovery_exception_returns_one_error_document
```

Output:

```text
FFF
AssertionError: 2 != 1
AssertionError: 2 != 1
AssertionError: -1 != 1
Ran 3 tests in 0.039s
FAILED (failures=3)
```

The two parser failures were terminating through argparse before JSON emission;
the discovery exception was raised before the previous JSON error envelope.

### GREEN

Focused JSON regressions:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.test_cli.CliIntegrationTests.test_json_invalid_theme_returns_one_error_document tests.test_cli.CliIntegrationTests.test_json_missing_input_returns_one_error_document tests.test_cli.CliIntegrationTests.test_json_discovery_exception_returns_one_error_document
```

```text
Ran 3 tests in 0.023s
OK
```

Final verification:

```powershell
& .\.venv\Scripts\python.exe -m py_compile src\md_changer\cli.py src\md_changer\gui.py
& .\.venv\Scripts\python.exe -m unittest tests.test_cli
& .\.venv\Scripts\python.exe -m unittest discover -s tests
git diff --check
```

```text
Ran 9 tests in 0.088s
OK
Ran 42 tests in 0.879s
OK
```

The JSON-aware parser captures argparse output only while parsing raw JSON-mode
arguments, returns one JSON error document with a message, and preserves
conventional argparse exits for non-JSON invocations. Discovery and CSS
preflight now execute inside the JSON error envelope. The GUI warning title is
`변환 실패` when every selected file fails, while mixed outcomes retain
`변환 완료 (일부 실패)`.

## Fix round: preserve JSON-mode help

### RED

Command:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.test_cli.CliIntegrationTests.test_json_help_preserves_argparse_help_and_success_exit
```

Output:

```text
F
AssertionError: 1 != 0
Ran 1 test in 0.011s
FAILED (failures=1)
```

`--json --help` was being treated as a validation error because the JSON parser
wrapper converted every `SystemExit` into an error result.

### GREEN

Focused help and JSON-validation regressions:

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.test_cli.CliIntegrationTests.test_json_help_preserves_argparse_help_and_success_exit tests.test_cli.CliIntegrationTests.test_json_invalid_theme_returns_one_error_document tests.test_cli.CliIntegrationTests.test_json_missing_input_returns_one_error_document
```

```text
Ran 3 tests in 0.026s
OK
```

Final verification:

```powershell
& .\.venv\Scripts\python.exe -m py_compile src\md_changer\cli.py src\md_changer\gui.py
& .\.venv\Scripts\python.exe -m unittest tests.test_cli
& .\.venv\Scripts\python.exe -m unittest discover -s tests
git diff --check
```

```text
Ran 10 tests in 0.108s
OK
Ran 43 tests in 0.946s
OK
```

The JSON argument wrapper now distinguishes `SystemExit(0)` from parser
validation failures. Help output remains conventional and exits successfully;
invalid JSON-mode arguments still emit exactly one JSON error document and exit
with status 1.

# Task 2 Report: Layered Theme Registry and Custom CSS

## Scope

Implemented the four built-in document themes, CSS layer composition, and
keyword-only theme/custom-CSS forwarding through HTML and PDF conversion. The
existing `PDF_CSS` remains available as a compatibility alias for the shared
print baseline. No Mermaid, GUI, CLI, packaging, or documentation work was
changed.

## TDD evidence

### RED

Command:

```powershell
uv run python -m unittest tests/test_themes.py -v
```

Output (exit 1):

```text
ERROR: test_themes (unittest.loader._FailedTest.test_themes)
ModuleNotFoundError: No module named 'md_changer.themes'
Ran 1 test in 0.000s
FAILED (errors=1)
```

This was the expected missing-feature failure after adding the focused tests.

### GREEN

Commands:

```powershell
uv run python -m unittest tests/test_themes.py -v
uv run python -m unittest discover -s tests -v
```

Output (both exit 0):

```text
Ran 5 tests in 0.150s
OK

Ran 14 tests in 0.218s
OK
```

## Files changed

- `src/md_changer/themes.py` — frozen `ThemeDefinition`, ordered built-in
  registry, retrieval/listing, validation, Mermaid mappings/variables, and
  CSS layer composition.
- `src/md_changer/styles.py` — promoted the old baseline to
  `COMMON_PRINT_CSS` and retained `PDF_CSS` as its compatibility alias.
- `src/md_changer/core.py` — added keyword-only `theme` and `custom_css`
  conversion plumbing while preserving the third positional `custom_css`
  argument of `build_html`.
- `tests/test_themes.py` — regression coverage for registry data, invalid
  themes, default baseline HTML, layer precedence, and conversion HTML.

## Self-review

- Confirmed the theme name order and labels exactly match the task brief.
- Confirmed unknown-theme errors include both the rejected value and all valid
  names.
- Confirmed CSS layers are emitted common → built-in → optional custom, with
  layer comments.
- Confirmed `PDF_CSS` remains importable and default HTML contains the former
  complete baseline.
- Confirmed the full unittest suite passes and `git diff --check` returns
  success (only Git line-ending warnings were emitted).

## Concerns

- `ThemeDefinition` is frozen, but its required `dict[str, str]`
  `mermaid_variables` field is shallowly mutable by Python callers. This
  follows the specified interface; future API hardening could use a mapping
  proxy if a deep-immutable mapping is desired.
- Mermaid variables are registry data only in this task. Offline Mermaid
  rendering and consumption of these variables are intentionally deferred to
  Task 3.

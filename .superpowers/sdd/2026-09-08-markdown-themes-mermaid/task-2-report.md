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

- Mermaid variables are registry data only in this task. Offline Mermaid
  rendering and consumption of these variables are intentionally deferred to
  Task 3.

## Fix round: deep immutability of Mermaid variables

### Root cause

`@dataclass(frozen=True)` protects reassignment of the
`mermaid_variables` attribute but does not make a nested `dict` immutable.
`get_theme()` and `list_themes()` return the shared definitions, so callers
could mutate the registry through that nested dictionary.

### RED

Command:

```powershell
uv run python -m unittest tests/test_themes.py -v
```

Output (exit 1):

```text
FAIL: test_built_in_mermaid_variables_cannot_mutate_the_shared_registry
AssertionError: TypeError not raised
Ran 6 tests in 0.131s
FAILED (failures=1)
```

### Fix and GREEN

Changed `ThemeDefinition.mermaid_variables` to the honest
`Mapping[str, str]` annotation and wrapped every built-in variable mapping in
`types.MappingProxyType`. The regression test assigns through the public
`get_theme("modern")` result, requires a `TypeError`, and then confirms the
registry value remains unchanged.

Commands:

```powershell
uv run python -m unittest tests/test_themes.py -v
uv run python -m unittest discover -s tests -v
```

Output (both exit 0):

```text
Ran 6 tests in 0.174s
OK

Ran 15 tests in 0.215s
OK
```

### Updated concern

The built-in `ThemeDefinition` values are now deeply immutable with respect to
their Mermaid-variable mappings. Mermaid rendering remains intentionally
deferred to Task 3.

# Multi-File Drag-and-Drop Design

**Goal:** Add drag-and-drop input and batch conversion so users can add multiple Markdown files and convert them to individual PDFs in one run.

## Scope

- Replace the single input file flow with a selected-file list
- Support multi-select file picking
- Support drag-and-drop for `.md` and `.markdown` files
- Convert all selected files into the chosen output folder
- Show a conversion result summary with success and failure counts

## Non-Goals

- Folder-based recursive scanning
- Parallel conversion
- Major module splitting or architecture refactor
- Full GUI automation test harness

## Recommended Approach

Keep the current Tkinter application structure and extend it with a list-based input model.

This is the smallest change that satisfies both requested features:
- drag-and-drop becomes another way to append files to the same list
- multi-file conversion becomes a loop over the selected file list

## UI Design

- Replace the single read-only input path field with a file list area
- Add `파일 추가`, `선택 제거`, `목록 비우기` controls
- Keep the output folder selector as a single destination
- Keep one main `PDF 변환` action button
- Show a short note that each Markdown file becomes a separate PDF in the selected output folder

## Data Model

- Store selected input files as an ordered list of normalized `Path` values
- Filter input to `.md` and `.markdown`
- Ignore duplicates when files are added again by dialog or drag-and-drop

## Conversion Flow

1. Validate that at least one Markdown file is selected
2. Validate that the output folder exists
3. Disable editing controls during conversion
4. Convert files sequentially in a background thread
5. Collect per-file success or failure results
6. Re-enable controls and show a summary dialog

## Error Handling

- Skip invalid extensions during add/drop and show a warning only if nothing valid was added
- If one file fails during batch conversion, continue processing the remaining files
- Report failed filenames and error count at the end

## Testing Strategy

- Add focused tests for file list normalization and duplicate removal if code is extracted into helper functions
- Run the existing build command after implementation
- Manually verify:
  - multi-select add
  - drag-and-drop add
  - remove/clear actions
  - batch conversion to multiple PDFs
  - mixed success/failure summary path

## Risks

- Native drag-and-drop support in Tkinter may require a lightweight additional dependency or Windows-specific handling
- If drag-and-drop support is more limited than expected in plain Tkinter, the fallback is to keep the multi-file UI complete and wire drag-and-drop through the smallest viable library integration

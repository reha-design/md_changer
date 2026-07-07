from __future__ import annotations

import html
import os
import sys
import threading
import uuid
from collections.abc import Iterable
from pathlib import Path
from tkinter import StringVar, filedialog, messagebox, ttk
import tkinter as tk

import markdown
from tkinterdnd2 import DND_FILES, TkinterDnD


APP_NAME = "Markdown PDF 변환기"
MARKDOWN_SUFFIXES = {".md", ".markdown"}


PDF_CSS = """
@page {
  size: A4;
  margin: 18mm 16mm;
}

* {
  box-sizing: border-box;
}

body {
  color: #202124;
  font-family: "Malgun Gothic", "Apple SD Gothic Neo", "Segoe UI", Arial, sans-serif;
  font-size: 14px;
  line-height: 1.65;
  margin: 0;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

h1, h2, h3, h4, h5, h6 {
  color: #111827;
  line-height: 1.28;
  margin: 1.2em 0 0.45em;
  page-break-after: avoid;
}

h1 {
  border-bottom: 1px solid #d8dee4;
  font-size: 28px;
  padding-bottom: 0.28em;
}

h2 {
  border-bottom: 1px solid #e5e7eb;
  font-size: 22px;
  padding-bottom: 0.22em;
}

h3 {
  font-size: 18px;
}

p, ul, ol, blockquote, pre, table {
  margin: 0.8em 0;
}

a {
  color: #0969da;
  text-decoration: none;
}

blockquote {
  border-left: 4px solid #d0d7de;
  color: #57606a;
  padding: 0.2em 1em;
}

code {
  background: #f6f8fa;
  border-radius: 4px;
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.92em;
  padding: 0.15em 0.35em;
}

pre {
  background: #f6f8fa;
  border: 1px solid #d8dee4;
  border-radius: 6px;
  line-height: 1.45;
  overflow-wrap: anywhere;
  padding: 12px;
  white-space: pre-wrap;
}

pre code {
  background: transparent;
  padding: 0;
}

table {
  border-collapse: collapse;
  display: table;
  page-break-inside: auto;
  width: 100%;
}

tr {
  page-break-inside: avoid;
}

th, td {
  border: 1px solid #d0d7de;
  padding: 7px 9px;
  vertical-align: top;
}

th {
  background: #f6f8fa;
  font-weight: 700;
}

img {
  display: block;
  height: auto;
  margin: 12px 0;
  max-width: 100%;
}

hr {
  border: 0;
  border-top: 1px solid #d8dee4;
  margin: 24px 0;
}
"""


def resource_path(relative_path: str) -> Path:
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return Path(base_path) / relative_path
    return Path(__file__).resolve().parent / relative_path


def configure_playwright_browser_path() -> None:
    bundled_browser_dir = resource_path("ms-playwright")
    if bundled_browser_dir.exists():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled_browser_dir)


def build_html(markdown_text: str, source_path: Path) -> str:
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

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <base href="{base_uri}">
  <title>{title}</title>
  <style>{PDF_CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def filter_new_markdown_files(
    raw_paths: Iterable[str], existing_files: Iterable[Path]
) -> tuple[list[Path], int]:
    """Filter candidate paths down to new, valid Markdown files.

    Returns the ordered list of files to add and a count of candidates
    skipped for having the wrong extension or already being present.
    """
    seen = {path.resolve() for path in existing_files}
    new_files: list[Path] = []
    skipped = 0
    for raw in raw_paths:
        path = Path(raw)
        if path.suffix.lower() not in MARKDOWN_SUFFIXES:
            skipped += 1
            continue
        resolved = path.resolve()
        if resolved in seen:
            skipped += 1
            continue
        seen.add(resolved)
        new_files.append(path)
    return new_files, skipped


def convert_markdown_to_pdf(input_file: Path, output_folder: Path, browser) -> Path:
    markdown_text = input_file.read_text(encoding="utf-8")
    output_file = output_folder / f"{input_file.stem}.pdf"
    html_text = build_html(markdown_text, input_file)

    html_file = output_folder / f".{input_file.stem}.md_changer_{uuid.uuid4().hex}.html"
    try:
        html_file.write_text(html_text, encoding="utf-8")

        page = browser.new_page()
        try:
            page.goto(html_file.resolve().as_uri(), wait_until="networkidle", timeout=30000)
            page.pdf(
                path=str(output_file),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
            )
        finally:
            page.close()
    finally:
        try:
            html_file.unlink(missing_ok=True)
        except OSError:
            pass

    return output_file


class MarkdownPdfApp:
    def __init__(self, root: TkinterDnD.Tk) -> None:
        self.root = root
        self.selected_files: list[Path] = []
        self.output_folder = StringVar()
        self.status = StringVar(value="변환할 Markdown 파일과 출력 폴더를 선택하세요.")
        self._converting = False

        self.root.title(APP_NAME)
        self.root.geometry("720x480")
        self.root.minsize(620, 420)

        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text=APP_NAME, font=("Malgun Gothic", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))

        ttk.Label(main, text="입력 파일 목록 (여기로 Markdown 파일을 끌어다 놓을 수 있습니다)").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )

        list_frame = ttk.Frame(main)
        list_frame.grid(row=2, column=0, columnspan=3, sticky="nsew", pady=(0, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.file_listbox = tk.Listbox(list_frame, selectmode="extended", activestyle="none")
        self.file_listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        self.file_listbox.drop_target_register(DND_FILES)
        self.file_listbox.dnd_bind("<<Drop>>", self.handle_drop)

        button_frame = ttk.Frame(main)
        button_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 16))
        self.add_button = ttk.Button(button_frame, text="파일 추가", command=self.select_input_files)
        self.add_button.pack(side="left")
        self.remove_button = ttk.Button(
            button_frame, text="선택 제거", command=self.remove_selected_files
        )
        self.remove_button.pack(side="left", padx=(8, 0))
        self.clear_button = ttk.Button(button_frame, text="목록 비우기", command=self.clear_files)
        self.clear_button.pack(side="left", padx=(8, 0))

        ttk.Label(main, text="출력 폴더").grid(row=4, column=0, sticky="w", pady=6)
        output_entry = ttk.Entry(main, textvariable=self.output_folder, state="readonly")
        output_entry.grid(row=4, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(main, text="출력 폴더 선택", command=self.select_output_folder).grid(
            row=4, column=2, sticky="ew", pady=6
        )

        self.convert_button = ttk.Button(main, text="PDF 변환", command=self.start_conversion)
        self.convert_button.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(20, 8))

        status_label = ttk.Label(main, textvariable=self.status, foreground="#4b5563")
        status_label.grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))

        note = ttk.Label(
            main,
            text="선택한 각 Markdown 파일은 같은 이름의 개별 PDF로 출력 폴더에 저장되며, 같은 이름의 PDF가 있으면 덮어씁니다.",
            foreground="#6b7280",
            wraplength=680,
        )
        note.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 0))

        main.columnconfigure(1, weight=1)
        main.rowconfigure(2, weight=1)

    def select_input_files(self) -> None:
        file_paths = filedialog.askopenfilenames(
            title="Markdown 파일 선택",
            filetypes=[("Markdown files", "*.md *.markdown"), ("All files", "*.*")],
        )
        if file_paths:
            self.add_files(file_paths)

    def select_output_folder(self) -> None:
        folder = filedialog.askdirectory(title="PDF 저장 폴더 선택")
        if folder:
            self.output_folder.set(folder)

    def handle_drop(self, event) -> None:
        if self._converting:
            return
        raw_paths = self.root.tk.splitlist(event.data)
        self.add_files(raw_paths)

    def add_files(self, raw_paths: Iterable[str]) -> None:
        new_files, skipped = filter_new_markdown_files(raw_paths, self.selected_files)
        if new_files:
            self.selected_files.extend(new_files)
            self._refresh_file_list()
            self.status.set(f"파일 {len(new_files)}개를 추가했습니다. (전체 {len(self.selected_files)}개)")
        elif skipped:
            messagebox.showwarning(
                APP_NAME, "추가할 수 있는 새 Markdown(.md, .markdown) 파일이 없습니다."
            )

    def remove_selected_files(self) -> None:
        selected_indexes = self.file_listbox.curselection()
        if not selected_indexes:
            return
        for index in reversed(selected_indexes):
            del self.selected_files[index]
        self._refresh_file_list()

    def clear_files(self) -> None:
        if not self.selected_files:
            return
        self.selected_files.clear()
        self._refresh_file_list()
        self.status.set("목록을 비웠습니다.")

    def _refresh_file_list(self) -> None:
        self.file_listbox.delete(0, tk.END)
        for path in self.selected_files:
            self.file_listbox.insert(tk.END, str(path))

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._converting = not enabled
        state = "normal" if enabled else "disabled"
        self.convert_button.configure(state=state)
        self.add_button.configure(state=state)
        self.remove_button.configure(state=state)
        self.clear_button.configure(state=state)

    def start_conversion(self) -> None:
        output_folder = Path(self.output_folder.get())

        if not self.selected_files:
            messagebox.showwarning(APP_NAME, "변환할 Markdown 파일을 추가하세요.")
            return
        if not self.output_folder.get():
            messagebox.showwarning(APP_NAME, "PDF가 저장될 출력 폴더를 선택하세요.")
            return
        if not output_folder.exists() or not output_folder.is_dir():
            messagebox.showwarning(APP_NAME, "선택한 출력 폴더를 찾을 수 없습니다.")
            return

        files = list(self.selected_files)
        self._set_controls_enabled(False)
        self.status.set(f"PDF 변환 중입니다... (0/{len(files)})")

        thread = threading.Thread(
            target=self._convert_in_background,
            args=(files, output_folder),
            daemon=True,
        )
        thread.start()

    def _convert_in_background(self, files: list[Path], output_folder: Path) -> None:
        configure_playwright_browser_path()

        from playwright.sync_api import sync_playwright

        total = len(files)
        results: list[tuple[Path, Path | None, str | None]] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for index, input_file in enumerate(files, start=1):
                    self.root.after(
                        0,
                        self.status.set,
                        f"PDF 변환 중입니다... ({index}/{total}) {input_file.name}",
                    )
                    try:
                        output_file = convert_markdown_to_pdf(input_file, output_folder, browser)
                    except Exception as exc:
                        results.append((input_file, None, str(exc)))
                    else:
                        results.append((input_file, output_file, None))
            finally:
                browser.close()

        self.root.after(0, self._conversion_finished, results)

    def _conversion_finished(
        self, results: list[tuple[Path, Path | None, str | None]]
    ) -> None:
        self._set_controls_enabled(True)

        failures = [(input_file, error) for input_file, _, error in results if error is not None]
        success_count = len(results) - len(failures)

        self.status.set(f"완료: 성공 {success_count}건, 실패 {len(failures)}건")

        summary_lines = [f"성공 {success_count}건 / 실패 {len(failures)}건"]
        if failures:
            summary_lines.append("")
            summary_lines.append("실패한 파일:")
            summary_lines.extend(f"- {input_file.name}: {error}" for input_file, error in failures)

        message = "\n".join(summary_lines)
        if failures:
            messagebox.showwarning(APP_NAME, message)
        else:
            messagebox.showinfo(APP_NAME, message)


def main() -> None:
    configure_playwright_browser_path()
    root = TkinterDnD.Tk()
    MarkdownPdfApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

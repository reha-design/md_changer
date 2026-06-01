from __future__ import annotations

import html
import os
import sys
import threading
import uuid
from pathlib import Path
from tkinter import Tk, StringVar, filedialog, messagebox, ttk

import markdown


APP_NAME = "Markdown PDF 변환기"


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


def convert_markdown_to_pdf(input_file: Path, output_folder: Path) -> Path:
    configure_playwright_browser_path()

    from playwright.sync_api import sync_playwright

    markdown_text = input_file.read_text(encoding="utf-8")
    output_file = output_folder / f"{input_file.stem}.pdf"
    html_text = build_html(markdown_text, input_file)

    html_file = output_folder / f".{input_file.stem}.md_changer_{uuid.uuid4().hex}.html"
    try:
        html_file.write_text(html_text, encoding="utf-8")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(html_file.resolve().as_uri(), wait_until="networkidle", timeout=30000)
            page.pdf(
                path=str(output_file),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
            )
            browser.close()
    finally:
        try:
            html_file.unlink(missing_ok=True)
        except OSError:
            pass

    return output_file


class MarkdownPdfApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.input_path = StringVar()
        self.output_folder = StringVar()
        self.status = StringVar(value="변환할 Markdown 파일과 출력 폴더를 선택하세요.")

        self.root.title(APP_NAME)
        self.root.geometry("720x310")
        self.root.minsize(620, 290)

        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text=APP_NAME, font=("Malgun Gothic", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))

        ttk.Label(main, text="입력 파일").grid(row=1, column=0, sticky="w", pady=6)
        input_entry = ttk.Entry(main, textvariable=self.input_path, state="readonly")
        input_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(main, text="입력 파일 선택", command=self.select_input_file).grid(
            row=1, column=2, sticky="ew", pady=6
        )

        ttk.Label(main, text="출력 폴더").grid(row=2, column=0, sticky="w", pady=6)
        output_entry = ttk.Entry(main, textvariable=self.output_folder, state="readonly")
        output_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(main, text="출력 폴더 선택", command=self.select_output_folder).grid(
            row=2, column=2, sticky="ew", pady=6
        )

        self.convert_button = ttk.Button(main, text="PDF 변환", command=self.start_conversion)
        self.convert_button.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(20, 8))

        status_label = ttk.Label(main, textvariable=self.status, foreground="#4b5563")
        status_label.grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))

        note = ttk.Label(
            main,
            text="출력 PDF는 입력 파일명과 같은 이름으로 저장되며, 같은 이름의 PDF가 있으면 덮어씁니다.",
            foreground="#6b7280",
        )
        note.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))

        main.columnconfigure(1, weight=1)

    def select_input_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Markdown 파일 선택",
            filetypes=[("Markdown files", "*.md *.markdown"), ("All files", "*.*")],
        )
        if file_path:
            self.input_path.set(file_path)

    def select_output_folder(self) -> None:
        folder = filedialog.askdirectory(title="PDF 저장 폴더 선택")
        if folder:
            self.output_folder.set(folder)

    def start_conversion(self) -> None:
        input_file = Path(self.input_path.get())
        output_folder = Path(self.output_folder.get())

        if not self.input_path.get():
            messagebox.showwarning(APP_NAME, "변환할 Markdown 파일을 선택하세요.")
            return
        if not input_file.exists() or not input_file.is_file():
            messagebox.showwarning(APP_NAME, "선택한 입력 파일을 찾을 수 없습니다.")
            return
        if input_file.suffix.lower() not in {".md", ".markdown"}:
            messagebox.showwarning(APP_NAME, "Markdown(.md, .markdown) 파일을 선택하세요.")
            return
        if not self.output_folder.get():
            messagebox.showwarning(APP_NAME, "PDF가 저장될 출력 폴더를 선택하세요.")
            return
        if not output_folder.exists() or not output_folder.is_dir():
            messagebox.showwarning(APP_NAME, "선택한 출력 폴더를 찾을 수 없습니다.")
            return

        self.convert_button.configure(state="disabled")
        self.status.set("PDF 변환 중입니다...")

        thread = threading.Thread(
            target=self._convert_in_background,
            args=(input_file, output_folder),
            daemon=True,
        )
        thread.start()

    def _convert_in_background(self, input_file: Path, output_folder: Path) -> None:
        try:
            output_file = convert_markdown_to_pdf(input_file, output_folder)
        except Exception as exc:
            self.root.after(0, self._conversion_failed, str(exc))
            return

        self.root.after(0, self._conversion_succeeded, output_file)

    def _conversion_succeeded(self, output_file: Path) -> None:
        self.convert_button.configure(state="normal")
        self.status.set(f"완료: {output_file}")
        messagebox.showinfo(APP_NAME, f"PDF 변환이 완료되었습니다.\n\n{output_file}")

    def _conversion_failed(self, error_message: str) -> None:
        self.convert_button.configure(state="normal")
        self.status.set("변환에 실패했습니다.")
        messagebox.showerror(APP_NAME, f"PDF 변환에 실패했습니다.\n\n{error_message}")


def main() -> None:
    configure_playwright_browser_path()
    root = Tk()
    MarkdownPdfApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

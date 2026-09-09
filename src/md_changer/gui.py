"""Tkinter GUI application for md_changer."""

from __future__ import annotations

import threading
from pathlib import Path

import tkinter as tk
from tkinter import StringVar, filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from md_changer.core import (
    APP_NAME,
    BatchConversionResult,
    ConversionResult,
    batch_convert_markdown_to_pdf_detailed,
    filter_new_markdown_files,
)
from md_changer.themes import list_themes


class MarkdownPdfApp:
    def __init__(self, root: TkinterDnD.Tk) -> None:
        self.root = root
        self.selected_files: list[Path] = []
        self.output_folder = StringVar()
        self.status = StringVar(value="변환할 Markdown 파일과 출력 폴더를 선택하세요.")
        self.themes = list_themes()
        self.theme_names = {theme.label: theme.name for theme in self.themes}
        self.selected_theme = StringVar(value=self.themes[0].label)
        self.css_path: Path | None = None
        self.css_display = StringVar(value="선택 안 함")
        self._converting = False

        self.root.title(APP_NAME)
        self.root.geometry("740x580")
        self.root.minsize(620, 500)

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
        button_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 12))
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
        self.output_button = ttk.Button(main, text="출력 폴더 선택", command=self.select_output_folder)
        self.output_button.grid(row=4, column=2, sticky="ew", pady=6)

        ttk.Label(main, text="문서 테마").grid(row=5, column=0, sticky="w", pady=6)
        self.theme_combobox = ttk.Combobox(
            main,
            textvariable=self.selected_theme,
            values=[theme.label for theme in self.themes],
            state="readonly",
        )
        self.theme_combobox.grid(row=5, column=1, columnspan=2, sticky="ew", padx=8, pady=6)

        ttk.Label(main, text="사용자 CSS (선택 사항)").grid(row=6, column=0, sticky="w", pady=6)
        css_entry = ttk.Entry(main, textvariable=self.css_display, state="readonly")
        css_entry.grid(row=6, column=1, sticky="ew", padx=8, pady=6)
        css_buttons = ttk.Frame(main)
        css_buttons.grid(row=6, column=2, sticky="ew", pady=6)
        self.css_select_button = ttk.Button(
            css_buttons, text="CSS 파일 선택", command=self.select_css_file
        )
        self.css_select_button.pack(side="left")
        self.css_clear_button = ttk.Button(css_buttons, text="CSS 해제", command=self.clear_css_file)
        self.css_clear_button.pack(side="left", padx=(6, 0))

        self.convert_button = ttk.Button(main, text="PDF 변환", command=self.start_conversion)
        self.convert_button.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(18, 8))

        status_label = ttk.Label(main, textvariable=self.status, foreground="#4b5563")
        status_label.grid(row=8, column=0, columnspan=3, sticky="w", pady=(8, 0))

        note = ttk.Label(
            main,
            text="참고: Playwright Chromium을 사용하여 Markdown을 HTML로 렌더링한 후 PDF로 변환합니다.",
            foreground="#6b7280",
            font=("Malgun Gothic", 9),
        )
        note.grid(row=9, column=0, columnspan=3, sticky="w", pady=(4, 0))

        main.columnconfigure(1, weight=1)
        main.rowconfigure(2, weight=1)

    def handle_drop(self, event) -> None:
        self.add_files(self.root.tk.splitlist(event.data))

    def select_input_files(self) -> None:
        raw_paths = filedialog.askopenfilenames(
            title="Markdown 파일 선택",
            filetypes=[("Markdown 파일", "*.md *.markdown"), ("모든 파일", "*.*")],
        )
        if raw_paths:
            self.add_files(raw_paths)

    def add_files(self, raw_paths: list[str] | tuple[str, ...]) -> None:
        new_files, skipped = filter_new_markdown_files(raw_paths, self.selected_files)
        if not new_files:
            if skipped > 0:
                messagebox.showinfo("알림", "추가할 수 있는 새로운 Markdown 파일이 없습니다.")
            return

        self.selected_files.extend(new_files)
        for file_path in new_files:
            self.file_listbox.insert("end", str(file_path))

        if not self.output_folder.get():
            self.output_folder.set(str(self.selected_files[0].parent.resolve()))

        if skipped > 0:
            self.status.set(
                f"{len(new_files)}개 파일 추가됨 ({skipped}개 제외: 확장자 미지원 또는 중복)."
            )
        else:
            self.status.set(f"{len(new_files)}개 파일이 목록에 추가되었습니다.")

    def remove_selected_files(self) -> None:
        selected_indices = list(self.file_listbox.curselection())
        if not selected_indices:
            return

        for index in reversed(selected_indices):
            self.file_listbox.delete(index)
            del self.selected_files[index]
        self.status.set(f"{len(selected_indices)}개 항목을 목록에서 제거했습니다.")

    def clear_files(self) -> None:
        self.selected_files.clear()
        self.file_listbox.delete(0, "end")
        self.status.set("파일 목록을 비웠습니다.")

    def select_output_folder(self) -> None:
        selected = filedialog.askdirectory(title="출력 폴더 선택")
        if selected:
            self.output_folder.set(str(Path(selected).resolve()))

    def select_css_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="CSS 파일 선택",
            filetypes=[("CSS 파일", "*.css"), ("모든 파일", "*.*")],
        )
        if selected:
            self.css_path = Path(selected).resolve()
            self.css_display.set(str(self.css_path))
            self.status.set("사용자 CSS 파일을 선택했습니다. 변환 시 모든 파일에 적용됩니다.")

    def clear_css_file(self) -> None:
        self.css_path = None
        self.css_display.set("선택 안 함")
        self.status.set("사용자 CSS 선택을 해제했습니다.")

    def start_conversion(self) -> None:
        if self._converting:
            return
        if not self.selected_files:
            messagebox.showwarning("경고", "변환할 Markdown 파일을 하나 이상 선택하세요.")
            return

        output_dir_str = self.output_folder.get().strip()
        if not output_dir_str:
            messagebox.showwarning("경고", "출력 폴더를 선택하세요.")
            return

        output_folder = Path(output_dir_str)
        theme = self.theme_names[self.selected_theme.get()]
        self.set_busy_state(True)
        self.status.set("Playwright 렌더러를 준비하는 중...")
        worker = threading.Thread(
            target=self._conversion_worker,
            args=(list(self.selected_files), output_folder, theme, self.css_path),
            daemon=True,
        )
        worker.start()

    def set_busy_state(self, busy: bool) -> None:
        self._converting = busy
        state = "disabled" if busy else "normal"
        self.add_button.configure(state=state)
        self.remove_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.output_button.configure(state=state)
        self.convert_button.configure(state=state)
        self.theme_combobox.configure(state="disabled" if busy else "readonly")
        self.css_select_button.configure(state=state)
        self.css_clear_button.configure(state=state)

    def _read_custom_css(self, css_path: Path | None) -> str | None:
        if css_path is None:
            return None
        resolved = css_path.resolve()
        if not resolved.is_file():
            raise ValueError(f"CSS path must be an existing file: {resolved}")
        try:
            return resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ValueError(f"Unable to read CSS file as UTF-8: {resolved}: {error}") from error

    def _conversion_worker(
        self,
        input_files: list[Path],
        output_folder: Path,
        theme: str,
        css_path: Path | None,
    ) -> None:
        try:
            custom_css = self._read_custom_css(css_path)

            def progress_cb(current: int, total: int, result: ConversionResult) -> None:
                detail = result.pdf.name if result.success and result.pdf else result.error
                self.root.after(
                    0,
                    self.status.set,
                    f"변환 중 ({current}/{total}): {result.source.name} - {detail}",
                )

            batch = batch_convert_markdown_to_pdf_detailed(
                input_files,
                output_folder,
                theme=theme,
                custom_css=custom_css,
                progress_callback=progress_cb,
            )
            self.root.after(0, self._on_conversion_complete, batch, output_folder)
        except Exception as exc:
            self.root.after(0, self._on_conversion_error, str(exc))

    def _on_conversion_complete(self, batch: BatchConversionResult, output_folder: Path) -> None:
        self.set_busy_state(False)
        self.status.set(
            f"변환 완료: 성공 {batch.converted_count}개, 실패 {batch.failed_count}개 ({output_folder})"
        )
        if batch.failed_count == 0:
            messagebox.showinfo(
                "변환 완료", f"성공 {batch.converted_count}개, 실패 0개\n저장 위치: {output_folder}"
            )
            return

        failed_files = "\n".join(
            f"- {result.source.name}: {result.error}"
            for result in batch.results
            if not result.success
        )
        messagebox.showwarning(
            "변환 실패" if batch.converted_count == 0 else "변환 완료 (일부 실패)",
            f"성공 {batch.converted_count}개, 실패 {batch.failed_count}개\n"
            f"저장 위치: {output_folder}\n\n실패 파일:\n{failed_files}",
        )

    def _on_conversion_error(self, error_message: str) -> None:
        self.set_busy_state(False)
        self.status.set("변환 중 오류가 발생했습니다.")
        messagebox.showerror("변환 오류", f"PDF 변환 중 오류가 발생했습니다:\n{error_message}")


def launch_gui() -> None:
    root = TkinterDnD.Tk()
    app = MarkdownPdfApp(root)
    root.mainloop()

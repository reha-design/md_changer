"""Tkinter GUI Application for md_changer."""

from __future__ import annotations

import threading
from pathlib import Path

from tkinter import StringVar, filedialog, messagebox, ttk
import tkinter as tk

from tkinterdnd2 import DND_FILES, TkinterDnD

from md_changer.core import (
    APP_NAME,
    batch_convert_markdown_to_pdf,
    configure_playwright_browser_path,
    filter_new_markdown_files,
)


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
            text="참고: Playwright Chromium을 사용하여 Markdown을 HTML로 렌더링한 후 PDF로 변환합니다.",
            foreground="#6b7280",
            font=("Malgun Gothic", 9),
        )
        note.grid(row=7, column=0, columnspan=3, sticky="w", pady=(4, 0))

        main.columnconfigure(1, weight=1)
        main.rowconfigure(2, weight=1)

    def handle_drop(self, event) -> None:
        raw_paths = self.root.tk.splitlist(event.data)
        self.add_files(raw_paths)

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
            first_folder = str(self.selected_files[0].parent.resolve())
            self.output_folder.set(first_folder)

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
        self.set_busy_state(True)
        self.status.set("Playwright 렌더러를 준비하는 중...")

        worker = threading.Thread(
            target=self._conversion_worker,
            args=(list(self.selected_files), output_folder),
            daemon=True,
        )
        worker.start()

    def set_busy_state(self, busy: bool) -> None:
        self._converting = busy
        state = "disabled" if busy else "normal"
        self.add_button.configure(state=state)
        self.remove_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.convert_button.configure(state=state)

    def _conversion_worker(self, input_files: list[Path], output_folder: Path) -> None:
        try:
            configure_playwright_browser_path()

            def progress_cb(current: int, total: int, src: Path, dist: Path):
                self.root.after(
                    0,
                    self.status.set,
                    f"변환 중 ({current}/{total}): {src.name} -> {dist.name}",
                )

            generated = batch_convert_markdown_to_pdf(
                input_files, output_folder, progress_callback=progress_cb
            )

            self.root.after(
                0,
                self._on_conversion_success,
                len(generated),
                output_folder,
            )
        except Exception as exc:
            self.root.after(0, self._on_conversion_error, str(exc))

    def _on_conversion_success(self, count: int, output_folder: Path) -> None:
        self.set_busy_state(False)
        self.status.set(f"변환 완료! 총 {count}개 PDF 저장: {output_folder}")
        messagebox.showinfo("성공", f"{count}개 Markdown 파일을 PDF로 변환했습니다.")

    def _on_conversion_error(self, error_message: str) -> None:
        self.set_busy_state(False)
        self.status.set("변환 중 오류가 발생했습니다.")
        messagebox.showerror("변환 오류", f"PDF 변환 중 오류가 발생했습니다:\n{error_message}")


def launch_gui() -> None:
    root = TkinterDnD.Tk()
    app = MarkdownPdfApp(root)
    root.mainloop()

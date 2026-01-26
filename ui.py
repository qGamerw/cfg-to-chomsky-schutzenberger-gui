"""Графический интерфейс Tkinter для конвертера CFG -> CS.

Приложение содержит вкладки для:
- ввода грамматики;
- краткого и подробного вывода конвертации;
- визуализации дерева разбора;
- справки по теореме;
- примеров и настроек;
- логов выполнения.
"""

import tkinter as tk
import tkinter.font as tkfont
import queue
import sys
import threading
import traceback
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from cs_representation import build_cs_representation, format_cs_output, format_cs_output_compact
from grammar import GrammarError, parse_grammar
from parse_tree import ParseError, parse_string
from ui_content import (
    DEMO_INFO_TEXT,
    EXAMPLE_1_GRAMMAR,
    EXAMPLE_1_INPUT,
    EXAMPLE_2_GRAMMAR,
    EXAMPLE_2_INPUT,
    EXAMPLE_3_GRAMMAR,
    EXAMPLE_3_INPUT,
    EXAMPLE_4_GRAMMAR,
    EXAMPLE_4_INPUT,
    THEOREM_TEXT,
)
from ui_tree_canvas import clear_tree_canvas, render_parse_tree


class CSConverterApp:
    """Основной контроллер GUI: собирает вкладки и обрабатывает действия."""

    def __init__(self, root):
        """Инициализирует состояние приложения, шрифты и все вкладки интерфейса."""
        self.root = root
        self.root.title("Конвертер КС-грамматики в нотацию Хомского–Шютценбергера")
        self.root.geometry("1000x720")

        # Общий шрифт для полей ввода/вывода (можно менять размер).
        try:
            self.io_font = tkfont.nametofont("TkFixedFont").copy()
        except tk.TclError:
            self.io_font = tkfont.Font(family="Courier", size=11)
        self.io_font.configure(size=11)

        self.font_size_var = tk.StringVar(value=str(int(self.io_font.cget("size"))))

        self.input_string_var = tk.StringVar(value="")
        self.tree_zoom = 1.0
        self.tree_zoom_var = tk.StringVar(value="100%")

        self._suppress_output_autoconvert = False

        self._last_parse_tree = None

        self._pending_logs = []
        self._console_log_queue = queue.Queue()
        self._log_worker_stop = threading.Event()
        self._conversion_cache = None
        self._tree_parse_cache = None
        self._demo_running = False
        self._demo_state_backup = {}
        self.show_scrollbars = False

        self.tree_canvas_font = self.io_font.copy()

        self._setup_exception_logging()
        self._init_styles()

        self._init_theorem_fonts()
        self._build_ui()
        self._start_log_worker()

    def _init_theorem_fonts(self):
        """Создает специальные варианты шрифтов для вкладки с теоремой."""
        base_size = int(self.io_font.cget("size"))
        self.theorem_title_font = self.io_font.copy()
        self.theorem_title_font.configure(weight="bold", size=base_size + 3)

        self.theorem_subtitle_font = self.io_font.copy()
        self.theorem_subtitle_font.configure(slant="italic", size=base_size)

        self.theorem_heading_font = self.io_font.copy()
        self.theorem_heading_font.configure(weight="bold", size=base_size + 1)

        self.theorem_subheading_font = self.io_font.copy()
        self.theorem_subheading_font.configure(weight="bold", size=base_size)

    def _init_styles(self):
        """Настраивает современную цветовую тему и стили ttk-виджетов."""
        self.colors = {
            "bg": "#f5f7fb",
            "panel": "#ffffff",
            "text": "#0f172a",
            "muted": "#475569",
            "accent": "#0ea5a4",
            "accent_active": "#0d9488",
            "secondary": "#e2e8f0",
            "secondary_active": "#cbd5e1",
            "danger": "#b91c1c",
            "field_bg": "#f8fafc",
            "border": "#cbd5e1",
        }

        self.root.configure(bg=self.colors["bg"])

        self.ui_font = tkfont.Font(family="Segoe UI", size=10)
        self.ui_font_bold = tkfont.Font(family="Segoe UI Semibold", size=10)
        self.header_font = tkfont.Font(family="Segoe UI Semibold", size=15)
        self.demo_popup_font = tkfont.Font(family="Segoe UI", size=16)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["panel"])

        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=self.ui_font)
        style.configure("Header.TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=self.header_font)
        style.configure("Muted.TLabel", background=self.colors["bg"], foreground=self.colors["muted"], font=self.ui_font)
        style.configure("Error.TLabel", background=self.colors["bg"], foreground=self.colors["danger"], font=self.ui_font)

        style.configure(
            "TButton",
            font=self.ui_font_bold,
            padding=(10, 6),
            relief="flat",
            borderwidth=0,
        )

        style.configure("Primary.TButton", background=self.colors["accent"], foreground="#ffffff")
        style.map(
            "Primary.TButton",
            background=[("active", self.colors["accent_active"]), ("pressed", self.colors["accent_active"])],
            foreground=[("disabled", "#cbd5e1")],
        )

        style.configure("Secondary.TButton", background=self.colors["secondary"], foreground=self.colors["text"])
        style.map(
            "Secondary.TButton",
            background=[("active", self.colors["secondary_active"]), ("pressed", self.colors["secondary_active"])],
        )

        style.configure("FileAction.TButton", background="#dbeafe", foreground="#0f172a")
        style.map(
            "FileAction.TButton",
            background=[("active", "#bfdbfe"), ("pressed", "#93c5fd")],
        )

        style.configure("Ghost.TButton", background=self.colors["panel"], foreground=self.colors["text"])
        style.map(
            "Ghost.TButton",
            background=[("active", "#f1f5f9"), ("pressed", "#e2e8f0")],
        )

        style.configure(
            "TEntry",
            fieldbackground=self.colors["field_bg"],
            foreground=self.colors["text"],
            padding=(6, 4),
        )

        style.configure("TNotebook", background=self.colors["bg"], tabmargins=(2, 2, 2, 0))
        style.configure(
            "TNotebook.Tab",
            font=self.ui_font_bold,
            padding=(12, 8),
            background="#e2e8f0",
            foreground=self.colors["muted"],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.colors["panel"]), ("active", "#f1f5f9")],
            foreground=[("selected", self.colors["text"]), ("active", self.colors["text"])],
        )

        # Убираем focus-элемент у вкладок, чтобы не было пунктирного выделения.
        try:
            base_tab_layout = style.layout("TNotebook.Tab")
            no_focus_layout = self._strip_focus_from_layout(base_tab_layout)
            if no_focus_layout:
                style.layout("NoFocus.TNotebook.Tab", no_focus_layout)
        except tk.TclError:
            pass

        style.configure("NoFocus.TNotebook", background=self.colors["bg"], tabmargins=(2, 2, 2, 0))
        style.configure(
            "NoFocus.TNotebook.Tab",
            font=self.ui_font_bold,
            padding=(12, 8),
            background="#e2e8f0",
            foreground=self.colors["muted"],
        )
        style.map(
            "NoFocus.TNotebook.Tab",
            background=[("selected", self.colors["panel"]), ("active", "#f1f5f9")],
            foreground=[("selected", self.colors["text"]), ("active", self.colors["text"])],
        )

        style.configure(
            "Vertical.TScrollbar",
            background="#cbd5e1",
            troughcolor="#f1f5f9",
        )
        style.configure(
            "Horizontal.TScrollbar",
            background="#cbd5e1",
            troughcolor="#f1f5f9",
        )

    def _strip_focus_from_layout(self, layout):
        """Удаляет focus-элементы из layout ttk, сохраняя структуру остальных узлов."""
        result = []
        for name, opts in layout:
            children = []
            if "children" in opts:
                children = self._strip_focus_from_layout(opts["children"])

            if "focus" in name.lower():
                # Не удаляем содержимое focus-узла: поднимаем его детей выше.
                result.extend(children)
                continue

            new_opts = dict(opts)
            if "children" in new_opts:
                new_opts["children"] = children
            result.append((name, new_opts))
        return result

    def _style_text_widget(self, widget: tk.Text):
        """Применяет единый визуальный стиль к текстовым полям Tk."""
        widget.configure(
            bg=self.colors["field_bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            selectbackground="#99f6e4",
            selectforeground=self.colors["text"],
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            padx=8,
            pady=8,
        )

    def _build_ui(self):
        """Создает и размещает все элементы интерфейса."""
        main_frame = ttk.Frame(self.root, padding=12, style="Card.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(
            main_frame,
            text="Конвертер КС-грамматики в нотацию Хомского–Шютценбергера",
            style="Header.TLabel",
        )
        header.pack(anchor=tk.W, pady=(0, 10))

        self.notebook = ttk.Notebook(main_frame, style="NoFocus.TNotebook", takefocus=False)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_input = ttk.Frame(self.notebook, padding=10, style="Card.TFrame")
        self.tab_output = ttk.Frame(self.notebook, padding=10, style="Card.TFrame")
        self.tab_output_detailed = ttk.Frame(self.notebook, padding=10, style="Card.TFrame")
        self.tab_tree = ttk.Frame(self.notebook, padding=10, style="Card.TFrame")
        self.tab_theorem = ttk.Frame(self.notebook, padding=10, style="Card.TFrame")
        self.tab_demo = ttk.Frame(self.notebook, padding=10, style="Card.TFrame")
        self.tab_settings = ttk.Frame(self.notebook, padding=10, style="Card.TFrame")
        self.tab_logs = ttk.Frame(self.notebook, padding=10, style="Card.TFrame")

        self.notebook.add(self.tab_input, text="Ввод грамматики")
        self.notebook.add(self.tab_output, text="Вывод")
        self.notebook.add(self.tab_output_detailed, text="Подробный вывод")
        self.notebook.add(self.tab_tree, text="Построить дерево")
        self.notebook.add(self.tab_theorem, text="Описание теоремы")
        self.notebook.add(self.tab_demo, text="Примеры")
        self.notebook.add(self.tab_settings, text="Настройки")
        self.notebook.add(self.tab_logs, text="Логи")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_tab_input()
        self._build_tab_output()
        self._build_tab_output_detailed()
        self._build_tab_tree()
        self._build_tab_theorem()
        self._build_tab_demo()
        self._build_tab_settings()
        self._build_tab_logs()

        self.notebook.select(self.tab_input)

    def _setup_exception_logging(self):
        """Подключает перехват исключений Tk/Python и отправляет их в вкладку логов."""
        def tk_callback_exception(exc_type, exc_value, exc_tb):
            self._log_exception("Tk callback exception", exc_type, exc_value, exc_tb)

        self.root.report_callback_exception = tk_callback_exception

        self._original_excepthook = sys.excepthook

        def global_excepthook(exc_type, exc_value, exc_tb):
            self._log_exception("Unhandled exception", exc_type, exc_value, exc_tb)
            if self._original_excepthook:
                self._original_excepthook(exc_type, exc_value, exc_tb)

        sys.excepthook = global_excepthook

    def _start_log_worker(self):
        """Запускает фоновый поток для вывода логов в консоль без блокировки UI."""
        self._log_worker_thread = threading.Thread(
            target=self._console_log_worker,
            name="console-log-worker",
            daemon=True,
        )
        self._log_worker_thread.start()

        # Аккуратно закрываем фоновый поток при закрытии окна.
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_request)

    def _on_close_request(self):
        """Останавливает фоновый поток логирования и закрывает окно."""
        self._log_worker_stop.set()
        try:
            self._console_log_queue.put_nowait(None)
        except Exception:
            pass
        self.root.destroy()

    def _console_log_worker(self):
        """Фоновый consumer: читает очередь логов и пишет в stdout."""
        while not self._log_worker_stop.is_set():
            try:
                message = self._console_log_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if message is None:
                break

            try:
                print(message)
            except UnicodeEncodeError:
                data = (message + "\n").encode("utf-8", errors="replace")
                try:
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                except Exception:
                    pass
            except Exception:
                pass

    def _on_tab_changed(self, event=None):
        """Автоматически запускает конвертацию при переходе на вкладки вывода."""
        if self._suppress_output_autoconvert:
            return
        try:
            selected = self.notebook.select()
        except tk.TclError:
            return
        tab_name = self.notebook.tab(selected, "text")
        self._console_log(f"[UI] Открыта вкладка: {tab_name}")

        if selected == str(self.tab_output):
            self.convert(switch_to_output_tab=False, source="авто: вкладка Вывод")
        elif selected == str(self.tab_output_detailed):
            self.convert(switch_to_output_tab=False, source="авто: вкладка Подробный вывод")

    def _select_output_tab(self):
        """Переключает на краткий вывод без рекурсивного запуска convert()."""
        self._suppress_output_autoconvert = True
        try:
            self.notebook.select(self.tab_output)
        finally:
            self._suppress_output_autoconvert = False

    def _select_tab_silent(self, tab):
        """Переключает вкладку без побочных авто-действий обработчика TabChanged."""
        self._suppress_output_autoconvert = True
        try:
            self.notebook.select(tab)
            self.root.update_idletasks()
        finally:
            self._suppress_output_autoconvert = False

    def _build_tab_input(self):
        """Собирает вкладку ввода грамматики с кнопками действий и примеров."""
        input_label = ttk.Label(self.tab_input, text="Ввод грамматики:")
        input_label.pack(anchor=tk.W)

        input_text_frame = ttk.Frame(self.tab_input)
        input_text_frame.pack(fill=tk.BOTH, expand=True)

        self.input_text = tk.Text(input_text_frame, height=12, wrap=tk.WORD, font=self.io_font)
        self._style_text_widget(self.input_text)
        input_scroll = None
        if self.show_scrollbars:
            input_scroll = ttk.Scrollbar(input_text_frame, orient=tk.VERTICAL, command=self.input_text.yview)
            self.input_text.configure(yscrollcommand=input_scroll.set)

        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if input_scroll is not None:
            input_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._install_clipboard_support(self.input_text)

        button_frame = ttk.Frame(self.tab_input)
        button_frame.pack(fill=tk.X, pady=10)

        left_col = ttk.Frame(button_frame)
        left_col.pack(side=tk.LEFT, anchor=tk.NW)

        right_col = ttk.Frame(button_frame)
        right_col.pack(side=tk.RIGHT, anchor=tk.NE)

        convert_button = ttk.Button(left_col, text="Конвертировать", command=self.convert, style="Primary.TButton")
        convert_button.pack(anchor=tk.W, fill=tk.X)

        build_tree_button = ttk.Button(
            left_col,
            text="Построить дерево",
            command=self._build_tree_from_input_tab,
            style="Secondary.TButton",
        )
        build_tree_button.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))

        load_cfg_button = ttk.Button(
            left_col,
            text="Загрузить КСГ",
            command=self._load_cfg_from_txt,
            style="FileAction.TButton",
        )
        load_cfg_button.pack(anchor=tk.W, fill=tk.X, pady=(10, 0))

        save_cfg_button = ttk.Button(
            left_col,
            text="Сохранить КСГ",
            command=self._save_cfg_to_txt,
            style="FileAction.TButton",
        )
        save_cfg_button.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))

        example1_button = ttk.Button(right_col, text="Пример 1", command=self.load_example1, style="Secondary.TButton")
        example1_button.pack(anchor=tk.W, fill=tk.X)

        example2_button = ttk.Button(right_col, text="Пример 2", command=self.load_example2, style="Secondary.TButton")
        example2_button.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))

        example3_button = ttk.Button(right_col, text="Пример 3", command=self.load_example3, style="Secondary.TButton")
        example3_button.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))

        example4_button = ttk.Button(right_col, text="Пример 4", command=self.load_example4, style="Secondary.TButton")
        example4_button.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))

    def _build_tree_from_input_tab(self):
        """Строит дерево разбора и открывает вкладку с деревом."""
        self.build_parse_tree()
        self.notebook.select(self.tab_tree)

    def _load_cfg_from_txt(self):
        """Загружает текст КС-грамматики из TXT-файла в поле ввода."""
        file_path = filedialog.askopenfilename(
            title="Загрузить КСГ",
            filetypes=[("Text files", "*.txt")],
            defaultextension=".txt",
        )
        if not file_path:
            self._console_log("[КСГ] Загрузка отменена пользователем")
            return

        try:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="cp1251") as f:
                    content = f.read()

            self._set_input(content)
            self._conversion_cache = None
            self._tree_parse_cache = None
            self._console_log(f"[КСГ] Файл загружен: {file_path}")
        except Exception as exc:
            self._console_log(f"[КСГ] Ошибка загрузки файла: {exc}")
            messagebox.showerror("Загрузка КСГ", f"Не удалось загрузить файл:\n{exc}")

    def _save_cfg_to_txt(self):
        """Сохраняет текущий текст КС-грамматики в TXT-файл."""
        file_path = filedialog.asksaveasfilename(
            title="Сохранить КСГ",
            filetypes=[("Text files", "*.txt")],
            defaultextension=".txt",
            initialfile="grammar.txt",
        )
        if not file_path:
            self._console_log("[КСГ] Сохранение отменено пользователем")
            return

        try:
            content = self.input_text.get("1.0", "end-1c")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._console_log(f"[КСГ] Файл сохранен: {file_path}")
            messagebox.showinfo("Сохранить КСГ", "Грамматика успешно сохранена.")
        except Exception as exc:
            self._console_log(f"[КСГ] Ошибка сохранения файла: {exc}")
            messagebox.showerror("Сохранить КСГ", f"Не удалось сохранить файл:\n{exc}")

    def _build_tab_output(self):
        """Собирает вкладку краткого вывода конвертации."""
        self.error_label = ttk.Label(self.tab_output, text="", style="Error.TLabel")
        self.error_label.pack(anchor=tk.W)
        self.error_label.pack_forget()

        output_label = ttk.Label(self.tab_output, text="Вывод:")
        output_label.pack(anchor=tk.W)

        output_text_frame = ttk.Frame(self.tab_output)
        output_text_frame.pack(fill=tk.BOTH, expand=True)

        self.output_text = tk.Text(
            output_text_frame,
            height=18,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=self.io_font,
        )
        self._style_text_widget(self.output_text)
        output_scroll = None
        if self.show_scrollbars:
            output_scroll = ttk.Scrollbar(output_text_frame, orient=tk.VERTICAL, command=self.output_text.yview)
            self.output_text.configure(yscrollcommand=output_scroll.set)
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if output_scroll is not None:
            output_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _show_output_error(self, message):
        """Показывает сообщение ошибки на вкладке краткого вывода."""
        self.error_label.config(text=message)
        if not self.error_label.winfo_ismapped():
            self.error_label.pack(anchor=tk.W, pady=(0, 8), before=self.output_text.master)

    def _clear_output_error(self):
        """Скрывает сообщение ошибки на вкладке краткого вывода."""
        self.error_label.config(text="")
        if self.error_label.winfo_ismapped():
            self.error_label.pack_forget()

    def _show_detailed_output_error(self, message):
        """Показывает сообщение ошибки на вкладке подробного вывода."""
        self.detailed_error_label.config(text=message)
        if not self.detailed_error_label.winfo_ismapped():
            self.detailed_error_label.pack(anchor=tk.W, pady=(0, 8), before=self.output_detailed_text.master)

    def _clear_detailed_output_error(self):
        """Скрывает сообщение ошибки на вкладке подробного вывода."""
        self.detailed_error_label.config(text="")
        if self.detailed_error_label.winfo_ismapped():
            self.detailed_error_label.pack_forget()

    def _show_conversion_error(self, message):
        """Показывает ошибку конвертации сразу на двух вкладках вывода."""
        self._show_output_error(message)
        self._show_detailed_output_error(message)

    def _clear_conversion_error(self):
        """Скрывает ошибку конвертации на двух вкладках вывода."""
        self._clear_output_error()
        self._clear_detailed_output_error()

    def _build_tab_output_detailed(self):
        """Собирает вкладку подробного вывода с шагами алгоритма."""
        self.detailed_error_label = ttk.Label(self.tab_output_detailed, text="", style="Error.TLabel")
        self.detailed_error_label.pack(anchor=tk.W)
        self.detailed_error_label.pack_forget()

        detailed_label = ttk.Label(self.tab_output_detailed, text="Подробный вывод:")
        detailed_label.pack(anchor=tk.W)

        detailed_text_frame = ttk.Frame(self.tab_output_detailed)
        detailed_text_frame.pack(fill=tk.BOTH, expand=True)

        self.output_detailed_text = tk.Text(
            detailed_text_frame,
            height=18,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=self.io_font,
        )
        self._style_text_widget(self.output_detailed_text)
        detailed_scroll = None
        if self.show_scrollbars:
            detailed_scroll = ttk.Scrollbar(
                detailed_text_frame,
                orient=tk.VERTICAL,
                command=self.output_detailed_text.yview,
            )
            self.output_detailed_text.configure(yscrollcommand=detailed_scroll.set)
        self.output_detailed_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if detailed_scroll is not None:
            detailed_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_tab_tree(self):
        """Собирает вкладку дерева разбора с Canvas и управлением масштабом."""
        label = ttk.Label(self.tab_tree, text="Построение дерева разбора для входной строки:")
        label.pack(anchor=tk.W)

        entry_label = ttk.Label(self.tab_tree, text="Входная строка:")
        entry_label.pack(anchor=tk.W, pady=(8, 0))

        self.tree_string_entry = ttk.Entry(self.tab_tree, textvariable=self.input_string_var)
        self.tree_string_entry.pack(fill=tk.X, expand=False)
        self._install_clipboard_support(self.tree_string_entry)

        button_frame = ttk.Frame(self.tab_tree)
        button_frame.pack(fill=tk.X, pady=10)

        build_button = ttk.Button(button_frame, text="Построить дерево", command=self.build_parse_tree, style="Primary.TButton")
        build_button.pack(side=tk.LEFT)

        save_button = ttk.Button(
            button_frame,
            text="Сохранить результат",
            command=self._save_tree_canvas_png,
            style="Secondary.TButton",
        )
        save_button.pack(side=tk.LEFT, padx=(12, 0))

        zoom_out_button = ttk.Button(button_frame, text="Масштаб -", command=self._zoom_tree_out, style="Ghost.TButton")
        zoom_out_button.pack(side=tk.RIGHT)

        zoom_label = ttk.Label(button_frame, textvariable=self.tree_zoom_var)
        zoom_label.pack(side=tk.RIGHT, padx=6)

        zoom_in_button = ttk.Button(button_frame, text="Масштаб +", command=self._zoom_tree_in, style="Ghost.TButton")
        zoom_in_button.pack(side=tk.RIGHT)

        self.tree_error_label = ttk.Label(self.tab_tree, text="", style="Error.TLabel")
        self.tree_error_label.pack(anchor=tk.W, pady=(0, 8))

        canvas_frame = ttk.Frame(self.tab_tree)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.tree_canvas = tk.Canvas(
            canvas_frame,
            background=self.colors["field_bg"],
            highlightthickness=1,
            highlightbackground=self.colors["border"],
        )
        y_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.tree_canvas.yview)
        x_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.tree_canvas.xview)
        self.tree_canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)

        self.tree_canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        self._install_canvas_scrolling(self.tree_canvas)
        self._clear_tree_canvas(message="Нажми 'Построить дерево' для визуализации.")

    def _build_tab_theorem(self):
        """Собирает вкладку теоремы и применяет форматирование текста."""
        label = ttk.Label(self.tab_theorem, text="Теорема Хомского–Шютценбергера:")
        label.pack(anchor=tk.W)

        text_frame = ttk.Frame(self.tab_theorem)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        theorem_text = tk.Text(text_frame, wrap=tk.WORD, height=18, font=self.io_font)
        self._style_text_widget(theorem_text)
        scroll = None
        if self.show_scrollbars:
            scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=theorem_text.yview)
            theorem_text.configure(yscrollcommand=scroll.set)
        theorem_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if scroll is not None:
            scroll.pack(side=tk.RIGHT, fill=tk.Y)

        theorem_text.insert("1.0", THEOREM_TEXT)
        self._format_theorem_text(theorem_text)
        theorem_text.config(state=tk.DISABLED)

        self.theorem_text_widget = theorem_text

    def _format_theorem_text(self, widget: tk.Text):
        """Применяет теги абзацев, заголовков и списков к тексту теоремы."""
        # Базовые теги
        widget.tag_configure(
            "p",
            lmargin1=32,
            lmargin2=12,
            spacing1=0,
            spacing3=10,
            justify=tk.LEFT,
        )
        widget.tag_configure(
            "title",
            font=self.theorem_title_font,
            spacing1=6,
            spacing3=8,
            justify=tk.LEFT,
        )
        widget.tag_configure(
            "subtitle",
            font=self.theorem_subtitle_font,
            spacing1=0,
            spacing3=10,
            justify=tk.LEFT,
        )
        widget.tag_configure(
            "h1",
            font=self.theorem_heading_font,
            spacing1=12,
            spacing3=6,
            lmargin1=0,
            lmargin2=0,
        )
        widget.tag_configure(
            "h2",
            font=self.theorem_subheading_font,
            spacing1=10,
            spacing3=4,
            lmargin1=0,
            lmargin2=0,
        )
        widget.tag_configure(
            "rule",
            lmargin1=0,
            lmargin2=0,
            spacing1=6,
            spacing3=10,
        )
        widget.tag_configure(
            "bullet",
            lmargin1=12,
            lmargin2=34,
            spacing1=0,
            spacing3=4,
        )

        text = widget.get("1.0", "end-1c")
        lines = text.splitlines()

        # Сбрасываем теги
        for tag in ("p", "title", "subtitle", "h1", "h2", "rule", "bullet"):
            widget.tag_remove(tag, "1.0", "end")

        def add_tag(tag: str, start_line: int, end_line: int):
            widget.tag_add(tag, f"{start_line}.0", f"{end_line}.end")

        def is_rule_line(s: str) -> bool:
            stripped = s.strip()
            return bool(stripped) and all(ch == "-" for ch in stripped) and len(stripped) >= 20

        def is_title_line(i: int, s: str) -> bool:
            return i == 1 and s.strip().startswith("ТЕОРЕМА ")

        def is_subtitle_line(i: int, s: str) -> bool:
            return i == 2 and s.strip().startswith("(") and s.strip().endswith(")")

        def is_section_header(s: str) -> bool:
            stripped = s.strip()
            if not stripped:
                return False
            # 1) ..., 2) ..., 3) ...
            if len(stripped) >= 2 and stripped[0].isdigit() and stripped[1:2] == ")":
                return True
            # 1.1 ..., 1.2 ...
            if stripped[:3].count(".") == 1 and stripped[0].isdigit() and stripped[2].isdigit() and stripped[3:4] == " ":
                return True
            return False

        def is_bullet(s: str) -> bool:
            return s.lstrip().startswith("- ")

        # Проставляем теги по типу строк/абзацев
        i = 1
        n = len(lines)
        while i <= n:
            s = lines[i - 1]
            if not s.strip():
                i += 1
                continue

            if is_title_line(i, s):
                add_tag("title", i, i)
                i += 1
                continue

            if is_subtitle_line(i, s):
                add_tag("subtitle", i, i)
                i += 1
                continue

            if is_rule_line(s):
                add_tag("rule", i, i)
                i += 1
                continue

            if is_bullet(s):
                start = i
                j = i
                while j <= n and lines[j - 1].strip() and is_bullet(lines[j - 1]):
                    j += 1
                end = j - 1
                add_tag("bullet", start, end)
                i = j
                continue

            if is_section_header(s):
                # Крупные разделы "1)" делаем H1, подпункты "1.1" - H2.
                stripped = s.strip()
                if len(stripped) >= 2 and stripped[0].isdigit() and stripped[1:2] == ")":
                    add_tag("h1", i, i)
                else:
                    add_tag("h2", i, i)
                i += 1
                continue

            # Обычный абзац: собираем до пустой строки
            start = i
            j = i
            while j <= n and lines[j - 1].strip():
                # не захватываем следующий заголовок/список/разделитель
                if j != start:
                    nxt = lines[j - 1]
                    if is_rule_line(nxt) or is_bullet(nxt) or is_section_header(nxt):
                        break
                j += 1
            end = j - 1
            add_tag("p", start, end)
            i = j

    def _build_tab_demo(self):
        """Собирает вкладку примеров с быстрыми кнопками и подсказками."""
        label = ttk.Label(
            self.tab_demo,
            text=(
                "Быстрый старт: выбери пример, нажми 'Конвертировать' и открой вкладку 'Вывод'."
            ),
            style="Muted.TLabel",
        )
        label.pack(anchor=tk.W)

        button_frame = ttk.Frame(self.tab_demo)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        example1_button = ttk.Button(button_frame, text="Загрузить пример 1", command=self.load_example1, style="Secondary.TButton")
        example1_button.pack(side=tk.LEFT)

        example2_button = ttk.Button(button_frame, text="Загрузить пример 2", command=self.load_example2, style="Secondary.TButton")
        example2_button.pack(side=tk.LEFT, padx=6)

        example3_button = ttk.Button(button_frame, text="Загрузить пример 3", command=self.load_example3, style="Secondary.TButton")
        example3_button.pack(side=tk.LEFT, padx=6)

        example4_button = ttk.Button(button_frame, text="Загрузить пример 4", command=self.load_example4, style="Secondary.TButton")
        example4_button.pack(side=tk.LEFT, padx=6)

        convert_button = ttk.Button(button_frame, text="Конвертировать", command=self.convert, style="Primary.TButton")
        convert_button.pack(side=tk.LEFT)

        demo_button = ttk.Button(button_frame, text="Демо", command=self._show_demo, style="Secondary.TButton")
        demo_button.pack(side=tk.LEFT, padx=(10, 0))

        info_label = ttk.Label(self.tab_demo, text="Особенности работы:")
        info_label.pack(anchor=tk.W, pady=(12, 0))

        info_frame = ttk.Frame(self.tab_demo)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        info_text = tk.Text(info_frame, wrap=tk.WORD, height=16, state=tk.NORMAL, font=self.io_font)
        self._style_text_widget(info_text)
        info_scroll = None
        if self.show_scrollbars:
            info_scroll = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=info_text.yview)
            info_text.configure(yscrollcommand=info_scroll.set)
        info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if info_scroll is not None:
            info_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        info_text.insert("1.0", DEMO_INFO_TEXT)
        info_text.config(state=tk.DISABLED)

    def _build_tab_settings(self):
        """Собирает вкладку настроек для управления размером шрифта."""
        label = ttk.Label(self.tab_settings, text="Настройки интерфейса:")
        label.pack(anchor=tk.W)

        font_frame = ttk.Frame(self.tab_settings)
        font_frame.pack(fill=tk.X, pady=(0, 0))

        font_label = ttk.Label(font_frame, text="Размер шрифта (ввод/вывод):")
        font_label.pack(side=tk.LEFT)

        font_entry = ttk.Entry(font_frame, width=6, textvariable=self.font_size_var)
        font_entry.pack(side=tk.LEFT, padx=8)
        font_entry.bind("<Return>", self._apply_font_size_event)
        font_entry.bind("<FocusOut>", self._apply_font_size_event)

    def _show_demo(self):
        """Запускает пошаговый сценарий демо по вкладкам приложения."""
        # Сначала загружаем пример 1 в поле ввода, затем блокируем интерфейс на время сценария.
        self.load_example1()
        self._select_tab_silent(self.tab_input)
        self._console_log("[Примеры] Демо: загружен пример 1 во вкладке 'Ввод грамматики'")

        self._set_demo_mode(True)
        try:
            self._console_log("[Примеры] Демо: запуск сценария")

            sections = self._get_demo_sections()

            def show_step(tab_name):
                text = sections.get(tab_name, "Описание шага не найдено.")
                self._show_demo_popup(tab_name, text)

            # 1) Ввод грамматики (пример 1 уже загружен перед запуском шагов)
            self._console_log("[Примеры] Демо: шаг 1/8 (Ввод грамматики)")
            show_step("Ввод грамматики")

            # 2) Вывод + конвертация
            self._select_tab_silent(self.tab_output)
            self.convert(switch_to_output_tab=False, source="демо: шаг 2")
            self._console_log("[Примеры] Демо: шаг 2/8 (Вывод)")
            show_step("Вывод")

            # 3) Подробный вывод + конвертация
            self._select_tab_silent(self.tab_output_detailed)
            self.convert(switch_to_output_tab=False, source="демо: шаг 3")
            self._console_log("[Примеры] Демо: шаг 3/8 (Подробный вывод)")
            show_step("Подробный вывод")

            # 4) Построить дерево + расчет дерева
            self._select_tab_silent(self.tab_tree)
            self.build_parse_tree()
            self._console_log("[Примеры] Демо: шаг 4/8 (Построить дерево)")
            show_step("Построить дерево")

            # 5) Описание теоремы
            self._select_tab_silent(self.tab_theorem)
            self._console_log("[Примеры] Демо: шаг 5/8 (Описание теоремы)")
            show_step("Описание теоремы")

            # 6) Примеры
            self._select_tab_silent(self.tab_demo)
            self._console_log("[Примеры] Демо: шаг 6/8 (Примеры)")
            show_step("Примеры")

            # 7) Настройки
            self._select_tab_silent(self.tab_settings)
            self._console_log("[Примеры] Демо: шаг 7/8 (Настройки)")
            show_step("Настройки")

            # 8) Логи
            self._select_tab_silent(self.tab_logs)
            self._console_log("[Примеры] Демо: шаг 8/8 (Логи)")
            show_step("Логи")

            # После завершения сценария возвращаем пользователя на вкладку примеров.
            self._select_tab_silent(self.tab_demo)
            self._console_log("[Примеры] Демо: сценарий завершен")
        finally:
            self._set_demo_mode(False)

    def _show_demo_popup(self, tab_name, text):
        """Показывает модальное окно демо с увеличенным шрифтом."""
        popup = tk.Toplevel(self.root)
        popup.title(f"Демо: {tab_name}")
        popup.transient(self.root)
        popup.configure(bg=self.colors["panel"])
        popup.geometry("860x520")
        popup.minsize(640, 380)

        frame = ttk.Frame(popup, padding=12, style="Card.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(frame, text=f"Вкладка: {tab_name}", style="Header.TLabel")
        title_label.pack(anchor=tk.W, pady=(0, 8))

        text_frame = ttk.Frame(frame, style="Card.TFrame")
        text_frame.pack(fill=tk.BOTH, expand=True)

        text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=self.demo_popup_font,
            state=tk.NORMAL,
            bg=self.colors["field_bg"],
            fg=self.colors["text"],
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            padx=10,
            pady=10,
        )
        scroll = None
        if self.show_scrollbars:
            scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scroll.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if scroll is not None:
            scroll.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget.insert("1.0", text)
        text_widget.config(state=tk.DISABLED)

        ok_button = ttk.Button(frame, text="Ок", command=popup.destroy, style="Primary.TButton")
        ok_button.pack(anchor=tk.E, pady=(10, 0))

        popup.grab_set()
        ok_button.focus_set()
        popup.protocol("WM_DELETE_WINDOW", popup.destroy)
        self.root.wait_window(popup)

    def _set_demo_mode(self, enabled):
        """Блокирует/разблокирует элементы UI на время демонстрационного сценария."""
        if enabled:
            if self._demo_running:
                return
            self._demo_running = True
            self._demo_state_backup = {}
            self._set_widget_tree_enabled(self.root, False)
        else:
            if not self._demo_running:
                return
            self._set_widget_tree_enabled(self.root, True)
            self._demo_running = False

    def _set_widget_tree_enabled(self, widget, enabled):
        """Рекурсивно меняет state у контролов, исключая Notebook."""
        self._set_widget_enabled(widget, enabled)
        for child in widget.winfo_children():
            self._set_widget_tree_enabled(child, enabled)

    def _set_widget_enabled(self, widget, enabled):
        """Ставит/восстанавливает state конкретного виджета, если поддерживается."""
        if isinstance(widget, ttk.Notebook):
            return

        try:
            current_state = str(widget.cget("state"))
        except tk.TclError:
            return

        if enabled:
            if widget in self._demo_state_backup:
                prev = self._demo_state_backup.pop(widget)
                try:
                    widget.configure(state=prev)
                except tk.TclError:
                    pass
        else:
            if widget not in self._demo_state_backup:
                self._demo_state_backup[widget] = current_state
            try:
                widget.configure(state="disabled")
            except tk.TclError:
                pass

    def _get_demo_sections(self):
        """Извлекает описания шагов демо из DEMO_INFO_TEXT по заголовкам вкладок."""
        sections = {}
        current = None
        buffer = []

        for raw_line in DEMO_INFO_TEXT.splitlines():
            line = raw_line.rstrip()
            if line.startswith("Вкладка '") and line.endswith("'"):
                if current is not None:
                    sections[current] = "\n".join(buffer).strip()
                current = line[len("Вкладка '") : -1]
                buffer = []
                continue

            if current is not None:
                buffer.append(line)

        if current is not None:
            sections[current] = "\n".join(buffer).strip()

        return sections

    def _build_tab_logs(self):
        """Собирает вкладку логов с событиями выполнения и ошибками."""
        label = ttk.Label(self.tab_logs, text="Логи приложения:")
        label.pack(anchor=tk.W)

        logs_frame = ttk.Frame(self.tab_logs)
        logs_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.logs_text = tk.Text(logs_frame, wrap=tk.WORD, state=tk.DISABLED, font=self.io_font)
        self._style_text_widget(self.logs_text)
        logs_scroll = None
        if self.show_scrollbars:
            logs_scroll = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=self.logs_text.yview)
            self.logs_text.configure(yscrollcommand=logs_scroll.set)
        self.logs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        if logs_scroll is not None:
            logs_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        if self._pending_logs:
            self.logs_text.config(state=tk.NORMAL)
            self.logs_text.insert("1.0", "".join(self._pending_logs))
            self.logs_text.config(state=tk.DISABLED)
            self.logs_text.see("end")
            self._pending_logs.clear()

    def _append_log(self, message):
        """Добавляет сообщение в лог (буфер или UI), сохраняя read-only режим."""
        if not message:
            return

        if not message.endswith("\n"):
            message = message + "\n"

        if not hasattr(self, "logs_text"):
            self._pending_logs.append(message)
            return

        self.logs_text.config(state=tk.NORMAL)
        self.logs_text.insert("end", message)
        self.logs_text.config(state=tk.DISABLED)
        self.logs_text.see("end")

    def _log_exception(self, title, exc_type, exc_value, exc_tb):
        """Форматирует и записывает полный traceback исключения в логи."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        block = [
            f"[{timestamp}] {title}",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)).rstrip("\n"),
            "",
        ]
        payload = "\n".join(block)
        self._append_log(payload)
        try:
            self._console_log_queue.put_nowait(payload)
        except Exception:
            pass

    def _install_clipboard_support(self, widget):
        """Включает вставку через контекстное меню по ПКМ."""

        def do_paste(_event=None):
            # Для Text используем встроенный tk_textPaste (лучше работает с выделением
            # и системным буфером обмена). Для Entry и прочих - вставляем вручную.
            if isinstance(widget, tk.Text):
                try:
                    widget.tk.call("tk_textPaste", str(widget))
                except tk.TclError:
                    return "break"
                return "break"

            try:
                text = widget.clipboard_get(selection="CLIPBOARD")
            except tk.TclError:
                return "break"

            # Если есть выделение, заменяем его.
            try:
                widget.delete("sel.first", "sel.last")
            except tk.TclError:
                pass

            widget.insert("insert", text)
            return "break"

        context_menu = tk.Menu(widget, tearoff=0)
        context_menu.add_command(label="Вставить", command=do_paste)

        def show_context_menu(event):
            try:
                widget.focus_set()
                if isinstance(widget, tk.Text):
                    widget.mark_set("insert", f"@{event.x},{event.y}")
                else:
                    widget.icursor(f"@{event.x}")
                    try:
                        widget.selection_clear()
                    except tk.TclError:
                        pass

                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                try:
                    context_menu.grab_release()
                except tk.TclError:
                    pass
            return "break"

        # Windows/Linux: Button-3, некоторые системы: Button-2.
        widget.bind("<Button-3>", show_context_menu)
        widget.bind("<Button-2>", show_context_menu)

    def _install_canvas_scrolling(self, canvas: tk.Canvas):
        """Добавляет прокрутку колесом мыши для Canvas дерева."""
        def on_mousewheel(event):
            # Windows: event.delta is +/-120 multiples
            if getattr(event, "state", 0) & 0x0001:  # Shift
                canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        canvas.bind("<MouseWheel>", on_mousewheel)

    def _apply_font_size_event(self, _event=None):
        """Событийная обертка для применения размера шрифта из настроек."""
        self._apply_font_size()
        return "break"

    def _set_tree_zoom(self, value):
        """Устанавливает масштаб дерева в диапазоне [0.5, 3.0] и перерисовывает Canvas."""
        if value < 0.5:
            value = 0.5
        if value > 3.0:
            value = 3.0
        prev_zoom = self.tree_zoom
        self.tree_zoom = value
        self.tree_zoom_var.set(f"{int(round(self.tree_zoom * 100))}%")
        if abs(prev_zoom - self.tree_zoom) > 1e-9:
            self._console_log(f"[Построить дерево] Масштаб: {self.tree_zoom_var.get()}")
        if self._last_parse_tree is not None:
            self._render_parse_tree(self._last_parse_tree)

    def _zoom_tree_in(self):
        """Увеличивает масштаб дерева на один шаг."""
        self._set_tree_zoom(self.tree_zoom + 0.1)

    def _zoom_tree_out(self):
        """Уменьшает масштаб дерева на один шаг."""
        self._set_tree_zoom(self.tree_zoom - 0.1)

    def _console_log(self, message):
        """Пишет сообщение в вкладку логов и в stdout (с Unicode-safe fallback)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._append_log(f"[{timestamp}] {message}")
        try:
            self._console_log_queue.put_nowait(message)
        except Exception:
            pass

    def _format_symbol_list(self, items, max_preview=40):
        """Форматирует список символов для логов с ограничением длины."""
        ordered = list(items)
        if len(ordered) <= max_preview:
            return ", ".join(ordered)
        preview = ", ".join(ordered[:max_preview])
        return f"{preview}, ... (+{len(ordered) - max_preview})"

    def _log_grammar_details(self, grammar):
        """Пишет подробные логи о разобранной грамматике."""
        nonterminals = sorted(grammar.nonterminals)
        terminals = sorted(grammar.terminals)
        self._console_log(
            "[Конвертация] Нетерминалы: "
            + self._format_symbol_list(nonterminals)
        )
        self._console_log(
            "[Конвертация] Терминалы: "
            + self._format_symbol_list(terminals)
        )

        for lhs in sorted(grammar.productions.keys()):
            alts = grammar.productions[lhs]
            self._console_log(f"[Конвертация] {lhs}: альтернатив = {len(alts)}")
            for rhs in alts:
                rhs_str = " ".join(rhs) if rhs else "ε"
                self._console_log(f"[Конвертация]   правило: {lhs} -> {rhs_str}")

    def _log_cs_details(self, grammar, cs_rep):
        """Пишет подробные логи о построенном CS-представлении."""
        expand_steps = sum(len(alts) for alts in grammar.productions.values())
        match_steps = len(grammar.terminals)
        self._console_log(
            "[Конвертация] CS-метрики: "
            f"|K|={len(cs_rep.stack_symbols)}, |Γ|={len(cs_rep.gamma_pairs)}, "
            f"expand={expand_steps}, match={match_steps}"
        )
        self._console_log("[Конвертация] K: " + self._format_symbol_list(cs_rep.stack_symbols))
        self._console_log("[Конвертация] R-шаблон: " + cs_rep.r_regex)
        self._console_log("[Конвертация] STEP: " + cs_rep.step_regex)

        print_rules = [f"]{t}->{t}" for t in sorted(grammar.terminals)]
        self._console_log("[Конвертация] PRINT-правила h: " + self._format_symbol_list(print_rules, max_preview=80))

    def _get_or_build_tree_parse(self, grammar, grammar_text, input_string):
        """Возвращает дерево разбора из кэша или строит заново для пары (грамматика, строка)."""
        norm_input = input_string.strip()
        cached = self._tree_parse_cache
        if (
            cached
            and cached.get("grammar_text") == grammar_text
            and cached.get("input_string") == norm_input
        ):
            return cached.get("parse_tree"), cached.get("error", ""), True

        parse_tree = None
        error = ""
        try:
            parse_tree = parse_string(grammar, input_string)
        except ParseError as exc:
            error = exc.message

        self._tree_parse_cache = {
            "grammar_text": grammar_text,
            "input_string": norm_input,
            "parse_tree": parse_tree,
            "error": error,
        }
        return parse_tree, error, False

    def _apply_font_size(self):
        """Проверяет и применяет размер шрифта для текстовых виджетов UI."""
        raw = (self.font_size_var.get() or "").strip()
        try:
            size = int(raw)
        except ValueError:
            size = int(self.io_font.cget("size"))

        if size < 6:
            size = 6
        if size > 48:
            size = 48

        self.io_font.configure(size=size)
        self.font_size_var.set(str(size))
        self._console_log(f"[Настройки] Размер шрифта установлен: {size}")

        # Обновляем шрифты теоремы (они копии базового).
        if hasattr(self, "theorem_title_font"):
            self.theorem_title_font.configure(size=size + 3)
        if hasattr(self, "theorem_subtitle_font"):
            self.theorem_subtitle_font.configure(size=size)
        if hasattr(self, "theorem_heading_font"):
            self.theorem_heading_font.configure(size=size + 1)
        if hasattr(self, "theorem_subheading_font"):
            self.theorem_subheading_font.configure(size=size)

        if self._last_parse_tree is not None and hasattr(self, "tree_canvas"):
            self._render_parse_tree(self._last_parse_tree)

    def _clear_tree_canvas(self, message: str = ""):
        """Очищает Canvas дерева и при необходимости показывает подсказку."""
        if not hasattr(self, "tree_canvas"):
            return
        clear_tree_canvas(
            self.tree_canvas,
            self.io_font,
            self.tree_canvas_font,
            self.tree_zoom,
            message,
        )

    def _save_tree_canvas_png(self):
        """Сохраняет текущее содержимое Canvas дерева в PNG-файл."""
        if not hasattr(self, "tree_canvas") or self._last_parse_tree is None:
            messagebox.showwarning("Сохранение", "Сначала построй дерево разбора.")
            self._console_log("[Построить дерево] Сохранение отменено: дерево отсутствует")
            return

        file_path = filedialog.asksaveasfilename(
            title="Сохранить дерево разбора",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
            initialfile="parse_tree.png",
        )
        if not file_path:
            self._console_log("[Построить дерево] Сохранение отменено пользователем")
            return

        try:
            from PIL import Image, ImageGrab

            self.tree_canvas.update_idletasks()
            canvas = self.tree_canvas

            # В режиме с тайлами рамка Canvas (highlight) может попадать в каждый
            # снимок и создавать видимые вертикальные/горизонтальные швы.
            # Временно отключаем highlight на время захвата.
            old_highlight_thickness = canvas.cget("highlightthickness")
            old_highlight_bg = canvas.cget("highlightbackground")
            old_highlight_color = canvas.cget("highlightcolor")
            canvas.configure(highlightthickness=0)
            canvas.update_idletasks()

            view_w = canvas.winfo_width()
            view_h = canvas.winfo_height()

            if view_w <= 1 or view_h <= 1:
                raise RuntimeError("Размер области рендера слишком мал для сохранения.")

            region_raw = canvas.cget("scrollregion")
            if not region_raw:
                bbox_all = canvas.bbox("all")
                if not bbox_all:
                    raise RuntimeError("На Canvas нет данных для сохранения.")
                x0, y0, x1, y1 = bbox_all
            else:
                x0, y0, x1, y1 = [float(v) for v in region_raw.split()]

            content_w = max(1, int(round(x1 - x0)))
            content_h = max(1, int(round(y1 - y0)))

            result = Image.new("RGB", (content_w, content_h), color=self.colors["panel"])

            # Сохраняем текущее положение прокрутки, чтобы вернуть после сохранения.
            orig_x = canvas.xview()
            orig_y = canvas.yview()

            max_x_start = max(content_w - view_w, 0)
            max_y_start = max(content_h - view_h, 0)

            x_starts = list(range(0, max_x_start + 1, max(view_w, 1)))
            y_starts = list(range(0, max_y_start + 1, max(view_h, 1)))
            if not x_starts or x_starts[-1] != max_x_start:
                x_starts.append(max_x_start)
            if not y_starts or y_starts[-1] != max_y_start:
                y_starts.append(max_y_start)

            tile_count = len(x_starts) * len(y_starts)
            self._console_log(
                "[Построить дерево] Сохранение PNG: "
                f"размер={content_w}x{content_h}, тайлов={tile_count}"
            )

            root_x = canvas.winfo_rootx()
            root_y = canvas.winfo_rooty()

            try:
                for y_start in y_starts:
                    y_frac = 0.0 if content_h <= 0 else (y_start / content_h)
                    canvas.yview_moveto(y_frac)

                    for x_start in x_starts:
                        x_frac = 0.0 if content_w <= 0 else (x_start / content_w)
                        canvas.xview_moveto(x_frac)
                        canvas.update_idletasks()

                        # Фактическая позиция может быть скорректирована Tk (на краях).
                        left = int(round(canvas.xview()[0] * content_w))
                        top = int(round(canvas.yview()[0] * content_h))

                        grab = ImageGrab.grab(
                            bbox=(root_x, root_y, root_x + view_w, root_y + view_h),
                            all_screens=True,
                        )

                        crop_w = min(view_w, content_w - left)
                        crop_h = min(view_h, content_h - top)
                        if crop_w <= 0 or crop_h <= 0:
                            continue

                        tile = grab.crop((0, 0, crop_w, crop_h))
                        result.paste(tile, (left, top))
            finally:
                # Возвращаем исходную прокрутку даже при ошибках.
                canvas.xview_moveto(orig_x[0])
                canvas.yview_moveto(orig_y[0])
                canvas.configure(
                    highlightthickness=old_highlight_thickness,
                    highlightbackground=old_highlight_bg,
                    highlightcolor=old_highlight_color,
                )
                canvas.update_idletasks()

            result.save(file_path, format="PNG")

            self._console_log(f"[Построить дерево] Результат сохранен: {file_path}")
            messagebox.showinfo("Сохранение", "Изображение успешно сохранено.")
        except Exception as exc:
            self._console_log(f"[Построить дерево] Ошибка сохранения PNG: {exc}")
            messagebox.showerror("Сохранение", f"Не удалось сохранить изображение:\n{exc}")

    def _render_parse_tree(self, root_node):
        """Отрисовывает дерево разбора в Canvas как связанные круглые узлы."""
        if not hasattr(self, "tree_canvas"):
            return
        render_parse_tree(
            self.tree_canvas,
            root_node,
            self.io_font,
            self.tree_canvas_font,
            self.tree_zoom,
        )

    def build_parse_tree(self):
        """Разбирает входную строку и обновляет графическое дерево разбора."""
        input_text = self.input_text.get("1.0", "end-1c")
        input_string = self.input_string_var.get()
        self._console_log("[Построить дерево] Запуск построения дерева")
        self._console_log(f"[Построить дерево] Длина входной строки: {len(input_string.strip())}")
        try:
            grammar = None
            cached_conversion = self._conversion_cache
            if (
                cached_conversion
                and cached_conversion.get("grammar_text") == input_text
                and cached_conversion.get("ok")
            ):
                grammar = cached_conversion.get("grammar")
                if grammar is not None:
                    self._console_log("[Построить дерево] Использована грамматика из кэша конвертации")

            if grammar is None:
                grammar = parse_grammar(input_text)

            self._console_log(
                "[Построить дерево] Грамматика: "
                f"N={len(grammar.nonterminals)}, Σ={len(grammar.terminals)}"
            )
            if not input_string.strip():
                self._last_parse_tree = None
                self._clear_tree_canvas(message="Введите входную строку и нажмите 'Построить дерево'.")
                self.tree_error_label.config(text="")
                self._console_log("[Построить дерево] Входная строка пустая")
                return

            parse_tree, parse_error, from_cache = self._get_or_build_tree_parse(grammar, input_text, input_string)
            if from_cache:
                self._console_log("[Построить дерево] Использован кэш дерева разбора")

            if parse_error:
                raise ParseError(parse_error)

            self._last_parse_tree = parse_tree
            self._render_parse_tree(parse_tree)
            self.tree_error_label.config(text="")
            self._console_log("[Построить дерево] Дерево успешно построено")
        except GrammarError as exc:
            self._last_parse_tree = None
            self._clear_tree_canvas(message="")
            self.tree_error_label.config(text=str(exc))
            self._console_log(f"[Построить дерево] Ошибка грамматики: {exc}")
        except ParseError as exc:
            self._last_parse_tree = None
            self._clear_tree_canvas(message="")
            self.tree_error_label.config(text=exc.message)
            self._console_log(f"[Построить дерево] Ошибка разбора: {exc.message}")

    def load_example1(self):
        """Вставляет пример 1 в поле ввода грамматики."""
        self._set_input(EXAMPLE_1_GRAMMAR)
        self.input_string_var.set(EXAMPLE_1_INPUT)
        self._console_log("[Примеры] Загружен пример 1")

    def load_example2(self):
        """Вставляет пример 2 в поле ввода грамматики."""
        self._set_input(EXAMPLE_2_GRAMMAR)
        self.input_string_var.set(EXAMPLE_2_INPUT)
        self._console_log("[Примеры] Загружен пример 2")

    def load_example3(self):
        """Вставляет пример 3 (арифметическая лексемная грамматика)."""
        self._set_input(EXAMPLE_3_GRAMMAR)
        self.input_string_var.set(EXAMPLE_3_INPUT)
        self._console_log("[Примеры] Загружен пример 3")

    def load_example4(self):
        """Вставляет пример 4 (команды доступа и токены)."""
        self._set_input(EXAMPLE_4_GRAMMAR)
        self.input_string_var.set(EXAMPLE_4_INPUT)
        self._console_log("[Примеры] Загружен пример 4")

    def _set_input(self, text):
        """Заменяет содержимое поля ввода грамматики."""
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)

    def convert(self, switch_to_output_tab=True, source="ручной запуск"):
        """Выполняет парсинг CFG и обновляет краткий/подробный вывод конвертации."""
        input_text = self.input_text.get("1.0", "end-1c")
        self._console_log(f"[Конвертация] Запуск ({source})")
        conversion_data = None
        cache = self._conversion_cache
        if cache and cache.get("grammar_text") == input_text:
            if not cache.get("ok"):
                error_text = cache.get("error", "Ошибка грамматики.")
                self._set_output("")
                self._set_output_detailed("")
                self._show_conversion_error(error_text)
                self._console_log("[Конвертация] Использован кэш ошибки (грамматика не изменялась)")
                if hasattr(self, "tree_canvas") and hasattr(self, "tree_error_label"):
                    self._last_parse_tree = None
                    self._clear_tree_canvas(message="")
                    self.tree_error_label.config(text=error_text)
                if switch_to_output_tab:
                    self._select_output_tab()
                return

            grammar_cached = cache.get("grammar")
            cs_rep_cached = cache.get("cs_rep")
            if grammar_cached is not None and cs_rep_cached is not None:
                conversion_data = cache
                self._console_log("[Конвертация] Использован кэш (грамматика без изменений)")

        if conversion_data is None:
            # Грамматика изменилась: сбрасываем кэш дерева для новой версии правил.
            self._tree_parse_cache = None
            try:
                self._console_log("[Конвертация] Шаг 1/4: парсинг грамматики")
                grammar = parse_grammar(input_text)

                productions_count = sum(len(alts) for alts in grammar.productions.values())
                self._console_log(
                    "[Конвертация] Грамматика разобрана: "
                    f"N={len(grammar.nonterminals)}, Σ={len(grammar.terminals)}, правил={productions_count}"
                )
                self._log_grammar_details(grammar)

                self._console_log("[Конвертация] Шаг 2/4: построение CS-представления (K, Γ, R, h)")
                cs_rep = build_cs_representation(grammar)
                self._log_cs_details(grammar, cs_rep)

                self._console_log("[Конвертация] Шаг 4/4: формирование текстового вывода")
                result_text = format_cs_output_compact(grammar, cs_rep)
                detailed_result_text = format_cs_output(grammar, cs_rep, None)

                conversion_data = {
                    "grammar_text": input_text,
                    "ok": True,
                    "error": "",
                    "grammar": grammar,
                    "cs_rep": cs_rep,
                    "result_text": result_text,
                    "detailed_result_text": detailed_result_text,
                }
                self._conversion_cache = conversion_data
            except GrammarError as exc:
                error_text = str(exc)
                self._conversion_cache = {
                    "grammar_text": input_text,
                    "ok": False,
                    "error": error_text,
                    "grammar": None,
                    "cs_rep": None,
                    "result_text": "",
                    "detailed_result_text": "",
                }
                self._set_output("")
                self._set_output_detailed("")
                self._show_conversion_error(error_text)
                self._console_log(f"[Конвертация] Ошибка: {error_text}")
                if hasattr(self, "tree_canvas") and hasattr(self, "tree_error_label"):
                    self._last_parse_tree = None
                    self._clear_tree_canvas(message="")
                    self.tree_error_label.config(text=error_text)
                if switch_to_output_tab:
                    self._select_output_tab()
                return

        grammar = conversion_data["grammar"]
        cs_rep = conversion_data["cs_rep"]
        result_text = conversion_data["result_text"]
        detailed_result_text = conversion_data["detailed_result_text"]

        self._set_output(result_text)
        self._set_output_detailed(detailed_result_text)
        self._console_log(
            "[Конвертация] Результат обновлен: "
            f"|K|={len(cs_rep.stack_symbols)}, |STEP-альтернатив|={cs_rep.step_regex.count('(')}"
        )

        input_string = self.input_string_var.get()
        parse_tree = None
        tree_parse_error = ""
        if input_string.strip():
            self._console_log("[Конвертация] Шаг 3/4: попытка построить дерево разбора")
            parse_tree, tree_parse_error, tree_cache_hit = self._get_or_build_tree_parse(
                grammar,
                input_text,
                input_string,
            )
            if tree_cache_hit:
                self._console_log("[Конвертация] Использован кэш дерева разбора")
            if tree_parse_error:
                self._console_log(f"[Конвертация] Дерево разбора: ошибка ({tree_parse_error})")
            else:
                self._console_log("[Конвертация] Дерево разбора: успешно")
        else:
            self._console_log("[Конвертация] Шаг 3/4: пропуск дерева (входная строка пуста)")

        if hasattr(self, "tree_canvas") and hasattr(self, "tree_error_label"):
            if parse_tree is not None:
                self._last_parse_tree = parse_tree
                self._render_parse_tree(parse_tree)
                self.tree_error_label.config(text="")
                self._console_log("[Конвертация] Дерево разбора синхронизировано")
            elif tree_parse_error:
                self._last_parse_tree = None
                self._clear_tree_canvas(message="")
                self.tree_error_label.config(text=tree_parse_error)
                self._console_log(f"[Конвертация] Дерево не построено: {tree_parse_error}")
            else:
                self._last_parse_tree = None
                self._clear_tree_canvas(message="Введите входную строку и нажмите 'Построить дерево'.")
                self.tree_error_label.config(text="")

        self._clear_conversion_error()
        self._console_log("[Конвертация] Завершено успешно")
        if switch_to_output_tab:
            self._select_output_tab()

    def _set_output(self, text):
        """Обновляет поле вывода, сохраняя его read-only."""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", text)
        self.output_text.config(state=tk.DISABLED)

    def _set_output_detailed(self, text):
        """Обновляет поле подробного вывода, сохраняя его read-only."""
        self.output_detailed_text.config(state=tk.NORMAL)
        self.output_detailed_text.delete("1.0", tk.END)
        self.output_detailed_text.insert("1.0", text)
        self.output_detailed_text.config(state=tk.DISABLED)

import tkinter as tk
from tkinter import ttk

from cs_representation import build_cs_representation, format_cs_output
from grammar import GrammarError, parse_grammar
from parse_tree import ParseError, format_parse_tree, parse_string


class CSConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Конвертер КС-грамматики в нотацию Хомского–Шютценбергера")
        self.root.geometry("1000x720")

        # Собираем элементы интерфейса при инициализации приложения.
        self._build_ui()

    def _build_ui(self):
        """Создает и размещает все элементы интерфейса."""
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(
            main_frame,
            text="Конвертер КС-грамматики в нотацию Хомского–Шютценбергера",
            font=("Arial", 14, "bold"),
        )
        header.pack(anchor=tk.W, pady=(0, 10))

        input_label = ttk.Label(main_frame, text="Ввод грамматики:")
        input_label.pack(anchor=tk.W)

        self.input_text = tk.Text(main_frame, height=12, wrap=tk.WORD)
        self.input_text.pack(fill=tk.BOTH, expand=False)

        # Поле для строки, по которой строится дерево разбора.
        string_label = ttk.Label(main_frame, text="Входная строка (для дерева разбора):")
        string_label.pack(anchor=tk.W, pady=(8, 0))

        self.string_entry = ttk.Entry(main_frame)
        self.string_entry.pack(fill=tk.X, expand=False)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        convert_button = ttk.Button(button_frame, text="Конвертировать", command=self.convert)
        convert_button.pack(side=tk.LEFT)

        example1_button = ttk.Button(button_frame, text="Пример 1", command=self.load_example1)
        example1_button.pack(side=tk.LEFT, padx=6)

        example2_button = ttk.Button(button_frame, text="Пример 2", command=self.load_example2)
        example2_button.pack(side=tk.LEFT)

        self.error_label = ttk.Label(main_frame, text="", foreground="#b00020")
        self.error_label.pack(anchor=tk.W, pady=(0, 8))

        output_label = ttk.Label(main_frame, text="Вывод:")
        output_label.pack(anchor=tk.W)

        self.output_text = tk.Text(main_frame, height=18, wrap=tk.WORD, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True)

    def load_example1(self):
        """Вставляет пример 1 в поле ввода грамматики."""
        example = 'S -> a S b | A\nA -> a A | ""'
        self._set_input(example)
        self.string_entry.delete(0, tk.END)
        self.string_entry.insert(0, "a a b b")

    def load_example2(self):
        """Вставляет пример 2 в поле ввода грамматики."""
        example = 'S -> A B | C\nA -> a A | a\nB -> b B | b\nC -> D c | ""\nD -> d D | d'
        self._set_input(example)
        self.string_entry.delete(0, tk.END)
        self.string_entry.insert(0, "a a b b")

    def _set_input(self, text):
        """Заменяет содержимое поля ввода грамматики."""
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", text)

    def convert(self):
        """Основной обработчик кнопки: парсинг, построение CS и дерева разбора."""
        input_text = self.input_text.get("1.0", "end-1c")
        try:
            grammar = parse_grammar(input_text)
            cs_rep = build_cs_representation(grammar)
            parse_tree_text = None
            input_string = self.string_entry.get()
            if input_string.strip():
                parse_tree = parse_string(grammar, input_string)
                parse_tree_text = format_parse_tree(parse_tree)
            else:
                parse_tree_text = "Входная строка не задана, дерево разбора не строилось."
            result_text = format_cs_output(grammar, cs_rep, parse_tree_text)
            self._set_output(result_text)
            self.error_label.config(text="")
        except GrammarError as exc:
            self._set_output("")
            self.error_label.config(text=str(exc))
        except ParseError as exc:
            self._set_output("")
            self.error_label.config(text=exc.message)

    def _set_output(self, text):
        """Обновляет поле вывода, сохраняя его read-only."""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", text)
        self.output_text.config(state=tk.DISABLED)

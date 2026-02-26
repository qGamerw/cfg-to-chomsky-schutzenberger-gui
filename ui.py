import tkinter as tk
import tkinter.font as tkfont
import sys
from tkinter import ttk

from cs_representation import build_cs_representation, format_cs_output
from grammar import GrammarError, parse_grammar
from parse_tree import ParseError, ParseNode, parse_string


class CSConverterApp:
    def __init__(self, root):
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

        self.tree_canvas_font = self.io_font.copy()

        self._init_theorem_fonts()

    def _init_theorem_fonts(self):
        base_size = int(self.io_font.cget("size"))
        self.theorem_title_font = self.io_font.copy()
        self.theorem_title_font.configure(weight="bold", size=base_size + 3)

        self.theorem_subtitle_font = self.io_font.copy()
        self.theorem_subtitle_font.configure(slant="italic", size=base_size)

        self.theorem_heading_font = self.io_font.copy()
        self.theorem_heading_font.configure(weight="bold", size=base_size + 1)

        self.theorem_subheading_font = self.io_font.copy()
        self.theorem_subheading_font.configure(weight="bold", size=base_size)

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

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_input = ttk.Frame(self.notebook, padding=10)
        self.tab_output = ttk.Frame(self.notebook, padding=10)
        self.tab_tree = ttk.Frame(self.notebook, padding=10)
        self.tab_theorem = ttk.Frame(self.notebook, padding=10)
        self.tab_demo = ttk.Frame(self.notebook, padding=10)
        self.tab_settings = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.tab_input, text="Ввод грамматики")
        self.notebook.add(self.tab_output, text="Вывод")
        self.notebook.add(self.tab_tree, text="Построить дерево")
        self.notebook.add(self.tab_theorem, text="Описание теоремы")
        self.notebook.add(self.tab_demo, text="Примеры")
        self.notebook.add(self.tab_settings, text="Настройки")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_tab_input()
        self._build_tab_output()
        self._build_tab_tree()
        self._build_tab_theorem()
        self._build_tab_demo()
        self._build_tab_settings()

        self.notebook.select(self.tab_input)

    def _on_tab_changed(self, event=None):
        if self._suppress_output_autoconvert:
            return
        try:
            selected = self.notebook.select()
        except tk.TclError:
            return
        if selected == str(self.tab_output):
            self.convert()

    def _select_output_tab(self):
        self._suppress_output_autoconvert = True
        try:
            self.notebook.select(self.tab_output)
        finally:
            self._suppress_output_autoconvert = False

    def _build_tab_input(self):
        input_label = ttk.Label(self.tab_input, text="Ввод грамматики:")
        input_label.pack(anchor=tk.W)

        input_text_frame = ttk.Frame(self.tab_input)
        input_text_frame.pack(fill=tk.BOTH, expand=True)

        self.input_text = tk.Text(input_text_frame, height=12, wrap=tk.WORD, font=self.io_font)
        input_scroll = ttk.Scrollbar(input_text_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=input_scroll.set)

        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._install_clipboard_support(self.input_text)

        button_frame = ttk.Frame(self.tab_input)
        button_frame.pack(fill=tk.X, pady=10)

        left_col = ttk.Frame(button_frame)
        left_col.pack(side=tk.LEFT, anchor=tk.NW)

        right_col = ttk.Frame(button_frame)
        right_col.pack(side=tk.RIGHT, anchor=tk.NE)

        convert_button = ttk.Button(left_col, text="Конвертировать", command=self.convert)
        convert_button.pack(anchor=tk.W, fill=tk.X)

        build_tree_button = ttk.Button(left_col, text="Построить дерево", command=self._build_tree_from_input_tab)
        build_tree_button.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))

        example1_button = ttk.Button(right_col, text="Пример 1", command=self.load_example1)
        example1_button.pack(anchor=tk.W, fill=tk.X)

        example2_button = ttk.Button(right_col, text="Пример 2", command=self.load_example2)
        example2_button.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))

        example3_button = ttk.Button(right_col, text="Пример 3", command=self.load_example3)
        example3_button.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))

        example4_button = ttk.Button(right_col, text="Пример 4", command=self.load_example4)
        example4_button.pack(anchor=tk.W, fill=tk.X, pady=(6, 0))

    def _build_tree_from_input_tab(self):
        self.build_parse_tree()
        self.notebook.select(self.tab_tree)

    def _build_tab_output(self):
        self.error_label = ttk.Label(self.tab_output, text="", foreground="#b00020")
        self.error_label.pack(anchor=tk.W, pady=(0, 8))

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
        output_scroll = ttk.Scrollbar(output_text_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_scroll.set)
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_tab_tree(self):
        label = ttk.Label(self.tab_tree, text="Построение дерева разбора для входной строки:")
        label.pack(anchor=tk.W)

        entry_label = ttk.Label(self.tab_tree, text="Входная строка:")
        entry_label.pack(anchor=tk.W, pady=(8, 0))

        self.tree_string_entry = ttk.Entry(self.tab_tree, textvariable=self.input_string_var)
        self.tree_string_entry.pack(fill=tk.X, expand=False)
        self._install_clipboard_support(self.tree_string_entry)

        button_frame = ttk.Frame(self.tab_tree)
        button_frame.pack(fill=tk.X, pady=10)

        build_button = ttk.Button(button_frame, text="Построить дерево", command=self.build_parse_tree)
        build_button.pack(side=tk.LEFT)

        zoom_out_button = ttk.Button(button_frame, text="Масштаб -", command=self._zoom_tree_out)
        zoom_out_button.pack(side=tk.RIGHT)

        zoom_label = ttk.Label(button_frame, textvariable=self.tree_zoom_var)
        zoom_label.pack(side=tk.RIGHT, padx=6)

        zoom_in_button = ttk.Button(button_frame, text="Масштаб +", command=self._zoom_tree_in)
        zoom_in_button.pack(side=tk.RIGHT)

        self.tree_error_label = ttk.Label(self.tab_tree, text="", foreground="#b00020")
        self.tree_error_label.pack(anchor=tk.W, pady=(0, 8))

        canvas_frame = ttk.Frame(self.tab_tree)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self.tree_canvas = tk.Canvas(canvas_frame, background="#ffffff", highlightthickness=0)
        y_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.tree_canvas.yview)
        x_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.tree_canvas.xview)
        self.tree_canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)

        self.tree_canvas.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        self._install_canvas_scrolling(self.tree_canvas)
        self._clear_tree_canvas(message="Нажми 'Построить дерево' для визуализации.")

    def _build_tab_theorem(self):
        label = ttk.Label(self.tab_theorem, text="Теорема Хомского–Шютценбергера:")
        label.pack(anchor=tk.W)

        text_frame = ttk.Frame(self.tab_theorem)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        theorem_text = tk.Text(text_frame, wrap=tk.WORD, height=18, font=self.io_font)
        scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=theorem_text.yview)
        theorem_text.configure(yscrollcommand=scroll.set)
        theorem_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        content = """
Любой контекстно-свободный язык (то, что описывается КС-грамматикой/стековым автоматом)
можно выразить через скобочные слова и простые (регулярные) ограничения.

Интуитивная схема такая: берём "универсальный" язык правильных скобок (Dyck),
отфильтровываем его регулярными ограничениями (конечным автоматом), а затем "переводим"
оставшиеся скобочные слова в нужные строки с помощью гомоморфизма (подстановки символов).

1) Мини-словарь

1.1 Алфавит, слово, язык
- Алфавит Sigma: конечный набор символов, например {a, b}.
- Слово: конечная строка над Sigma, например "aabbb".
- Язык L: множество слов, L ⊆ Sigma*.

1.2 Регулярный язык (Regular language)
Язык, который распознаётся конечным автоматом (FA) или задаётся регулярным выражением.
Интуитивно: "памяти почти нет" (только конечное число состояний).

1.3 Контекстно-свободный язык (Context-Free Language, CFL)
Язык, который задаётся контекстно-свободной грамматикой (CFG) или распознаётся
магазинным автоматом (PDA) — автоматом со стеком.
Интуитивно: "есть стек", поэтому поддерживается вложенность/согласование чисел и т.п.

1.4 Dyck-язык (язык правильных скобочных последовательностей)
Dyck(Gamma) — язык правильных скобочных слов над набором типов скобок Gamma.
Свойства:
- скобки корректно вложены;
- нельзя закрыть скобку, если соответствующая ей не была открыта;
- типы должны совпадать (нельзя открыть "[" и закрыть ")").

Пример (1 тип скобок "[" и "]"):
- в Dyck: "[]", "[[]]", "[][]"
- не в Dyck: "][", "[]]", "[["

1.5 Пересечение языков
(D ∩ R) — слова, которые одновременно принадлежат D и принадлежат R.

1.6 Гомоморфизм строк (string homomorphism)
Функция h: Gamma* -> Sigma* (где Gamma — некоторый алфавит), такая что:
- каждому символу x из Gamma сопоставляется строка h(x) над Sigma (возможно пустая);
- для строки x1 x2 ... xk: h(x1 x2 ... xk) = h(x1) h(x2) ... h(xk).
Часто h "стирает" служебные символы, отправляя их в пустую строку (eps).

2) Формулировка теоремы
Язык L является контекстно-свободным ТОГДА И ТОЛЬКО ТОГДА, когда существуют:
- Dyck-язык D = Dyck(Gamma) над некоторым типизированным скобочным алфавитом Gamma,
- регулярный язык R (над тем же алфавитом Gamma),
- гомоморфизм h,

такие что:
L = h( D ∩ R )

Говоря проще:
* D гарантирует "правильную стековую/скобочную дисциплину",
* R добавляет регулярные (конечные, локальные) ограничения,
* h превращает оставшееся в конечный результат (и может стереть служебное).

3) Подробный пример: L = { a^n b^n | n >= 0 }
Это классический контекстно-свободный язык: сколько 'a', столько 'b',
и все 'a' идут перед всеми 'b'.

Шаг 1. Выбираем Dyck-язык D
Пусть Gamma = { [, ] } и D = Dyck(Gamma).
То есть D — все правильные скобочные последовательности из "[" и "]".

Шаг 2. Выбираем регулярный фильтр R
Хотим оставить только строки, где сначала идут все "[", а потом все "]":
R = "["* "]"*
(ноль или больше "[", затем ноль или больше "]")
Это регулярный язык.

Шаг 3. Находим пересечение D ∩ R
Если строка имеет вид "["* "]"* и при этом является правильной скобочной,
то она обязана быть ровно:
"["^n "]"^n  (n >= 0)
То есть:
D ∩ R = { "["^n "]"^n | n >= 0 }

Шаг 4. Задаём гомоморфизм h
Определим:
h("[") = "a"
h("]") = "b"

Тогда для любого n:
h( "["^n "]"^n ) = "a"^n "b"^n

Итого:
h( D ∩ R ) = { a^n b^n | n >= 0 } = L

Проверка на n=3:
Слово из D ∩ R:  "[[[]]]"
После h:          "aaabbb"

4) Почему это вообще работает (интуиция через стек)
Контекстно-свободные языки распознаются PDA (стековым автоматом).
Работу стека можно закодировать скобками:

- "push X"  -> открыть скобку типа X
- "pop X"   -> закрыть скобку типа X

Тогда корректная работа стека автоматически становится условием Dyck
(правильная вложенность и совпадение типов).

Дальше:
- регулярный язык R проверяет, что последовательность шагов автомата допустима
  (переходы между конечными состояниями — это проверка "конечным автоматом").
- гомоморфизм h извлекает/печатает терминалы входного языка и стирает служебное.

5) Практическая заметка
Теорема говорит, что D, R и h существуют, но "конструкция в лоб" часто получается
большой: алфавит скобок раздувается, а регулярный фильтр R может быть громоздким.
Это нормальная цена за универсальность результата.

Краткий итог:
CFL = h( Dyck ∩ Regular )
Контекстно-свободность = (скобочная/стековая дисциплина) + (регулярные ограничения) + (проекция в выход).
"""

        theorem_text.insert("1.0", content)
        self._format_theorem_text(theorem_text)
        theorem_text.config(state=tk.DISABLED)

        self.theorem_text_widget = theorem_text

    def _format_theorem_text(self, widget: tk.Text):
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
        label = ttk.Label(
            self.tab_demo,
            text=(
                "Быстрый старт: выбери пример, нажми 'Конвертировать' и открой вкладку 'Вывод'."
            ),
        )
        label.pack(anchor=tk.W)

        button_frame = ttk.Frame(self.tab_demo)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        example1_button = ttk.Button(button_frame, text="Загрузить пример 1", command=self.load_example1)
        example1_button.pack(side=tk.LEFT)

        example2_button = ttk.Button(button_frame, text="Загрузить пример 2", command=self.load_example2)
        example2_button.pack(side=tk.LEFT, padx=6)

        example3_button = ttk.Button(button_frame, text="Загрузить пример 3", command=self.load_example3)
        example3_button.pack(side=tk.LEFT, padx=6)

        example4_button = ttk.Button(button_frame, text="Загрузить пример 4", command=self.load_example4)
        example4_button.pack(side=tk.LEFT, padx=6)

        convert_button = ttk.Button(button_frame, text="Конвертировать", command=self.convert)
        convert_button.pack(side=tk.LEFT)

        info_label = ttk.Label(self.tab_demo, text="Особенности работы:")
        info_label.pack(anchor=tk.W, pady=(12, 0))

        info_frame = ttk.Frame(self.tab_demo)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        info_text = tk.Text(info_frame, wrap=tk.WORD, height=16, state=tk.NORMAL, font=self.io_font)
        info_scroll = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=info_text.yview)
        info_text.configure(yscrollcommand=info_scroll.set)
        info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        info_content = (
            "1) Правила ввода грамматики\n"
            "- Формат правила: A -> альтернатива1 | альтернатива2 | ...\n"
            "- Поддерживаются стрелки: -> и →\n"
            "- Альтернатива может быть пустой (ε): ε, epsilon или \"\"\n"
            "- Нетерминалы: Start, Expr, NumProd, TokenId и т.д.\n"
            "- Терминалы-лексемы не разбиваются на буквы: read, write, read_write, token_id\n"
            "- Лексемы в кавычках считаются одним терминалом:\n"
            "  \"read_write\" -> read_write, \"ISSUE(tenant=\" -> ISSUE(tenant=\n"
            "- Компактная запись тоже поддерживается: P(NumProd) токенизируется как\n"
            "  P, (, NumProd, )\n"
            "- Для неоднозначных многосимвольных токенов рекомендуется ставить пробелы\n\n"
            "2) Пункт конвертации\n"
            "- Кнопка 'Конвертировать' парсит грамматику и строит представление:\n"
            "  K = N ∪ Σ ∪ {⊥}, Γ, STEP, R и гомоморфизм h\n"
            "- На вкладке 'Вывод' показываются:\n"
            "  [SECTION K], [SECTION Γ], [SECTION R], [SECTION Вывод через h], [SECTION h]\n"
            "- Секция 'Вывод через h' объясняет, где появляется итоговая строка языка\n"
            "- При переходе на вкладку 'Вывод' конвертация запускается автоматически\n"
            "3) Построение дерева\n"
            "- Вкладка 'Построить дерево' строит графическое дерево разбора\n"
            "- Входную строку можно вводить с пробелами и без пробелов\n"
            "- Листья выравниваются по одной линии\n"
            "- Доступен масштаб: кнопки 'Масштаб +' и 'Масштаб -'\n\n"
            "4) Настройки\n"
            "- Во вкладке 'Настройки' задается размер шрифта полей ввода и вывода\n"
            "- Значение применяется по Enter или при потере фокуса\n\n"
            "5) Быстрые примеры\n"
            "- Пример 1: S -> a S b | A; A -> a A | ε (базовый CFG)\n"
            "- Пример 2: несколько нетерминалов A/B/C/D и ε-ветка\n"
            "- Пример 3: арифметика P((1+2+3))/P((4-5)) с NumProd/DenProd\n"
            "- Пример 4: лексемная grammar команд ISSUE/REFRESH/VALIDATE/INTROSPECT/REVOKE/ROTATE_KEYS\n"
            "- Рекомендуемый сценарий: загрузить пример -> Конвертировать -> посмотреть 'Вывод'\n"
            "  -> при необходимости открыть 'Построить дерево'"
        )

        info_text.insert("1.0", info_content)
        info_text.config(state=tk.DISABLED)

    def _build_tab_settings(self):
        label = ttk.Label(self.tab_settings)
        label.pack(anchor=tk.W)

        font_frame = ttk.Frame(self.tab_settings)
        font_frame.pack(fill=tk.X, pady=(0, 0))

        font_label = ttk.Label(font_frame, text="Размер шрифта (ввод/вывод):")
        font_label.pack(side=tk.LEFT)

        font_entry = ttk.Entry(font_frame, width=6, textvariable=self.font_size_var)
        font_entry.pack(side=tk.LEFT, padx=8)
        font_entry.bind("<Return>", self._apply_font_size_event)
        font_entry.bind("<FocusOut>", self._apply_font_size_event)

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
        def on_mousewheel(event):
            # Windows: event.delta is +/-120 multiples
            if getattr(event, "state", 0) & 0x0001:  # Shift
                canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        canvas.bind("<MouseWheel>", on_mousewheel)

    def _apply_font_size_event(self, _event=None):
        self._apply_font_size()
        return "break"

    def _set_tree_zoom(self, value):
        if value < 0.5:
            value = 0.5
        if value > 3.0:
            value = 3.0
        self.tree_zoom = value
        self.tree_zoom_var.set(f"{int(round(self.tree_zoom * 100))}%")
        if self._last_parse_tree is not None:
            self._render_parse_tree(self._last_parse_tree)

    def _zoom_tree_in(self):
        self._set_tree_zoom(self.tree_zoom + 0.1)

    def _zoom_tree_out(self):
        self._set_tree_zoom(self.tree_zoom - 0.1)

    def _console_log(self, message):
        try:
            print(message)
        except UnicodeEncodeError:
            data = (message + "\n").encode("utf-8", errors="replace")
            try:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            except Exception:
                pass

    def _apply_font_size(self):
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
        if not hasattr(self, "tree_canvas"):
            return
        canvas = self.tree_canvas
        canvas.delete("all")
        if message:
            base_size = int(self.io_font.cget("size"))
            zoom_size = max(6, int(round(base_size * self.tree_zoom)))
            self.tree_canvas_font.configure(size=zoom_size)
            canvas.create_text(
                16,
                16,
                text=message,
                anchor="nw",
                font=self.tree_canvas_font,
                fill="#334155",
            )
        bbox = canvas.bbox("all")
        canvas.configure(scrollregion=bbox if bbox else (0, 0, 1, 1))

    def _render_parse_tree(self, root_node):
        if not hasattr(self, "tree_canvas"):
            return

        canvas = self.tree_canvas
        canvas.delete("all")

        class _VisNode:
            __slots__ = ("label", "children", "x", "y", "depth")

            def __init__(self, label: str, children: list["_VisNode"]):
                self.label = label
                self.children = children
                self.x = 0.0
                self.y = 0.0
                self.depth = 0

        def normalize(n) -> _VisNode:
            if isinstance(n, ParseNode):
                kids = []
                for ch in n.children:
                    if isinstance(ch, ParseNode):
                        kids.append(normalize(ch))
                    else:
                        kids.append(_VisNode(str(ch), []))
                return _VisNode(str(n.symbol), kids)
            return _VisNode(str(n), [])

        vis_root = normalize(root_node)

        # Collect nodes for drawing.
        nodes: list[_VisNode] = []

        def collect(n: _VisNode):
            nodes.append(n)
            for c in n.children:
                collect(c)

        collect(vis_root)

        # Node size: use a single circle radius so levels are consistent.
        base_size = int(self.io_font.cget("size"))
        zoom_size = max(6, int(round(base_size * self.tree_zoom)))
        self.tree_canvas_font.configure(size=zoom_size)

        max_text_w = 0
        for n in nodes:
            w = int(self.tree_canvas_font.measure(n.label))
            if w > max_text_w:
                max_text_w = w

        radius = max(int(12 * self.tree_zoom), int(max_text_w / 2) + int(10 * self.tree_zoom))
        diameter = 2 * radius

        # Layout: compute subtree widths in pixels and place children under parents.
        h_gap = max(radius + int(20 * self.tree_zoom), int(28 * self.tree_zoom))
        v_gap = max(2 * radius + int(54 * self.tree_zoom), int(82 * self.tree_zoom))
        margin_x = radius + int(24 * self.tree_zoom)
        margin_y = radius + int(24 * self.tree_zoom)

        def subtree_width(n: _VisNode) -> float:
            if not n.children:
                return float(diameter)
            kids_w = sum(subtree_width(c) for c in n.children)
            kids_w += h_gap * (len(n.children) - 1)
            return float(max(diameter, kids_w))

        def assign_positions(n: _VisNode, left: float, depth: int):
            n.depth = depth
            n.y = float(depth)

            w = subtree_width(n)
            if not n.children:
                n.x = left + w / 2
                return

            kids_widths = [subtree_width(c) for c in n.children]
            kids_span = sum(kids_widths) + h_gap * (len(kids_widths) - 1)
            cur_left = left + (w - kids_span) / 2
            child_centers: list[float] = []
            for c, cw in zip(n.children, kids_widths):
                assign_positions(c, cur_left, depth + 1)
                child_centers.append(c.x)
                cur_left += cw + h_gap

            n.x = (min(child_centers) + max(child_centers)) / 2

        assign_positions(vis_root, 0.0, 0)

        # Выравниваем все конечные листья по одной нижней линии.
        leaf_nodes = [n for n in nodes if not n.children]
        max_leaf_depth = max((n.depth for n in leaf_nodes), default=0)
        for n in nodes:
            if not n.children:
                n.y = float(max_leaf_depth)
            else:
                n.y = float(n.depth)

        def to_px(n: _VisNode):
            return (margin_x + n.x, margin_y + n.y * v_gap)

        # Draw edges first.
        def draw_edges(n: _VisNode):
            x0, y0 = to_px(n)
            for c in n.children:
                x1, y1 = to_px(c)
                canvas.create_line(
                    x0,
                    y0 + radius,
                    x1,
                    y1 - radius,
                    fill="#334155",
                    width=max(1.0, 1.2 * self.tree_zoom),
                )
                draw_edges(c)

        draw_edges(vis_root)

        # Draw nodes on top.
        for n in nodes:
            x, y = to_px(n)
            is_leaf = not n.children
            fill = "#ffffff" if is_leaf else "#f1f5f9"
            canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                outline="#0f172a",
                width=max(1.0, 1.2 * self.tree_zoom),
                fill=fill,
            )
            canvas.create_text(x, y, text=n.label, font=self.tree_canvas_font, fill="#0f172a")

        bbox = canvas.bbox("all")
        if bbox:
            x0, y0, x1, y1 = bbox
            pad = 20
            canvas.configure(scrollregion=(x0 - pad, y0 - pad, x1 + pad, y1 + pad))
        else:
            canvas.configure(scrollregion=(0, 0, 1, 1))

    def build_parse_tree(self):
        input_text = self.input_text.get("1.0", "end-1c")
        input_string = self.input_string_var.get()
        try:
            grammar = parse_grammar(input_text)
            if not input_string.strip():
                self._last_parse_tree = None
                self._clear_tree_canvas(message="Введите входную строку и нажмите 'Построить дерево'.")
                self.tree_error_label.config(text="")
                return

            parse_tree = parse_string(grammar, input_string)
            self._last_parse_tree = parse_tree
            self._render_parse_tree(parse_tree)
            self.tree_error_label.config(text="")
        except GrammarError as exc:
            self._last_parse_tree = None
            self._clear_tree_canvas(message="")
            self.tree_error_label.config(text=str(exc))
        except ParseError as exc:
            self._last_parse_tree = None
            self._clear_tree_canvas(message="")
            self.tree_error_label.config(text=exc.message)

    def load_example1(self):
        """Вставляет пример 1 в поле ввода грамматики."""
        example = 'S -> a S b | A\nA -> a A | ""'
        self._set_input(example)
        self.input_string_var.set("a a b b")

    def load_example2(self):
        """Вставляет пример 2 в поле ввода грамматики."""
        example = 'S -> A B | C\nA -> a A | a\nB -> b B | b\nC -> D c | ""\nD -> d D | d'
        self._set_input(example)
        self.input_string_var.set("a a b b")

    def load_example3(self):
        """Вставляет пример 3 (арифметическая лексемная грамматика)."""
        example = (
            "Start -> Expr\n"
            "Expr -> P(NumProd) / P(DenProd)\n"
            "NumProd -> NumFactor | NumFactor * NumProd\n"
            "DenProd -> DenFactor | DenFactor * DenProd\n"
            "NumFactor -> ( Int + Int + Int )\n"
            "DenFactor -> ( Int - Int )\n"
            "Int -> Digit | Digit Int\n"
            "Digit -> 0|1|2|3|4|5|6|7|8|9"
        )
        self._set_input(example)
        self.input_string_var.set("P((1+2+3))/P((4-5))")

    def load_example4(self):
        """Вставляет пример 4 (команды доступа и токены)."""
        example = (
            "Start -> Cmd\n"
            "Cmd -> Issue | Refresh | Validate | Introspect | Revoke | RotateKeys\n"
            "Issue -> ISSUE ( tenant = TenantId , client = ClientId , user = UserId , scope = Scope , ttl = Num )"
            " | ISSUE ( client = ClientId , user = UserId , scope = Scope , ttl = Num )\n"
            "Refresh -> REFRESH ( token_id = TokenId , ttl = Num )\n"
            "Validate -> VALIDATE ( token_id = TokenId )\n"
            "Introspect -> INTROSPECT ( token_id = TokenId )\n"
            "Revoke -> REVOKE ( token_id = TokenId )\n"
            "RotateKeys -> ROTATE_KEYS ( tenant = TenantId , kid = Kid ) | ROTATE_KEYS ( kid = Kid )\n"
            "TenantId -> T Num\n"
            "ClientId -> C Num\n"
            "UserId -> U Num\n"
            "TokenId -> J Num\n"
            "Kid -> K Num\n"
            "Scope -> read | write | read_write | admin\n"
            "Num -> Digit | Digit Num\n"
            "Digit -> 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9"
        )
        self._set_input(example)
        self.input_string_var.set("REVOKE(token_id=J1)")

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
            input_string = self.input_string_var.get()
            parse_tree = None
            tree_parse_error = ""
            if input_string.strip():
                try:
                    parse_tree = parse_string(grammar, input_string)
                except ParseError as exc:
                    tree_parse_error = exc.message
            # Во вкладке "Вывод" показываем только CS-представление (без дерева разбора).
            result_text = format_cs_output(grammar, cs_rep, None)
            self._set_output(result_text)
            self._console_log("\n[Конвертация] Результат:\n" + result_text + "\n")
            if hasattr(self, "tree_canvas") and hasattr(self, "tree_error_label"):
                if parse_tree is not None:
                    self._last_parse_tree = parse_tree
                    self._render_parse_tree(parse_tree)
                    self.tree_error_label.config(text="")
                elif tree_parse_error:
                    self._last_parse_tree = None
                    self._clear_tree_canvas(message="")
                    self.tree_error_label.config(text=tree_parse_error)
                else:
                    self._last_parse_tree = None
                    self._clear_tree_canvas(message="Введите входную строку и нажмите 'Построить дерево'.")
                    self.tree_error_label.config(text="")
            self.error_label.config(text="")
            self._select_output_tab()
        except GrammarError as exc:
            self._set_output("")
            self.error_label.config(text=str(exc))
            self._console_log(f"\n[Конвертация] Ошибка: {exc}\n")
            if hasattr(self, "tree_canvas") and hasattr(self, "tree_error_label"):
                self._last_parse_tree = None
                self._clear_tree_canvas(message="")
                self.tree_error_label.config(text=str(exc))
            self._select_output_tab()

    def _set_output(self, text):
        """Обновляет поле вывода, сохраняя его read-only."""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", text)
        self.output_text.config(state=tk.DISABLED)

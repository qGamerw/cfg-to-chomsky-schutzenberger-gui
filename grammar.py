"""Публичный API парсинга грамматики и модель данных.

Модуль предоставляет основную точку входа для преобразования текстовой
КС-грамматики в токенизированные продукции.
Низкоуровневый лексический разбор вынесен в ``grammar_lexer``.
"""

import grammar_lexer as lex

EPSILON_SYMBOLS = {"ε", "epsilon", '""'}
# Символы, которые трактуются как пустая строка (epsilon) при вводе.

ARROW_SYMBOLS = ("->", "→")


class GrammarError(Exception):
    """Ошибка парсинга с понятным сообщением и номером строки (опционально)."""

    def __init__(self, message, line_no=None):
        """Создает объект ошибки парсинга грамматики.

        Параметры:
            message: Текст ошибки.
            line_no: Номер строки с ошибкой (если известен).
        """
        self.message = message
        self.line_no = line_no
        super().__init__(self.__str__())

    def __str__(self):
        """Возвращает форматированное сообщение об ошибке."""
        if self.line_no is None:
            return self.message
        return f"Строка {self.line_no}: {self.message}"


class Grammar:
    """Внутреннее представление токенизированной КС-грамматики."""

    def __init__(self, productions, start_symbol):
        """Инициализирует грамматику и вычисляет множества N и Σ.

        Параметры:
            productions: Словарь правил вида {LHS: [RHS1, RHS2, ...]}.
            start_symbol: Стартовый нетерминал.
        """
        self.productions = productions
        self.start_symbol = start_symbol
        self.nonterminals = set(productions.keys())
        self.terminals = self._collect_terminals()

    def _collect_terminals(self):
        """Собирает терминальные символы из всех правых частей правил."""
        terminals = set()
        for alts in self.productions.values():
            for alt in alts:
                for symbol in alt:
                    if symbol not in self.nonterminals:
                        terminals.add(symbol)
        return terminals


def parse_grammar(text):
    """Парсит текст грамматики в объект ``Grammar``."""
    if not text.strip():
        raise GrammarError(
            "Пустой ввод грамматики. Добавьте хотя бы одно правило в формате "
            "A -> α (например: S -> a S b | ε)."
        )

    productions = {}
    start_symbol = None

    raw_rules = []
    current_lhs = None

    for idx, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        if any(arrow in line for arrow in ARROW_SYMBOLS):
            lhs, rhs = split_rule_arrow(line, idx)
            lhs = normalize_nonterminal(lhs.strip())
            if not lhs:
                raise GrammarError(
                    "Пустая левая часть правила. Перед стрелкой должен быть нетерминал "
                    "(например: Expr -> Term).",
                    idx,
                )

            current_lhs = lhs
            if start_symbol is None:
                start_symbol = lhs

            alternatives = split_alternatives(rhs, idx)
            if not alternatives:
                raise GrammarError(
                    "Отсутствует правая часть правила. После стрелки укажите хотя бы одну "
                    "альтернативу (например: S -> A B | c).",
                    idx,
                )

            raw_rules.append((idx, lhs, alternatives))
            productions.setdefault(lhs, [])
            continue

        if line.startswith("|"):
            if current_lhs is None:
                raise GrammarError(
                    "Альтернатива '|' без предыдущего правила. Символ '|' можно использовать "
                    "только как продолжение уже начатого правила.",
                    idx,
                )
            rhs_cont = line[1:]
            alternatives = split_alternatives(rhs_cont, idx)
            if not alternatives:
                raise GrammarError(
                    "Отсутствует правая часть правила после '|'. Укажите альтернативу "
                    "(например: | Term).",
                    idx,
                )
            raw_rules.append((idx, current_lhs, alternatives))
            continue

        raise GrammarError(
            "Отсутствует '->' (или '→') в правиле. Используйте формат: "
            "Нетерминал -> правая_часть.",
            idx,
        )

    if start_symbol is None:
        raise GrammarError(
            "Не найден стартовый символ. Проверьте, что в тексте есть хотя бы одно "
            "непустое правило вида A -> α."
        )

    nonterminals = set(productions.keys())
    for idx, lhs, alternatives in raw_rules:
        for alt in alternatives:
            if alt in EPSILON_SYMBOLS or alt == "":
                productions[lhs].append([])
                continue
            productions[lhs].append(tokenize_rhs(alt, idx, nonterminals))

    return Grammar(productions, start_symbol)


def split_rule_arrow(line, line_no):
    """Делит строку правила по стрелке ``->`` или ``→``."""
    return lex.split_rule_arrow(line, line_no, GrammarError, ARROW_SYMBOLS)


def split_alternatives(rhs, line_no):
    """Делит RHS по ``|``, игнорируя ``|`` внутри кавычек."""
    return lex.split_alternatives(rhs, line_no, GrammarError)


def normalize_nonterminal(token):
    """Нормализует запись нетерминала (``<Expr>`` -> ``Expr``)."""
    return lex.normalize_nonterminal(token)


def tokenize_rhs(alt, line_no, nonterminals=None):
    """Токенизирует одну альтернативу RHS в символы грамматики."""
    nonterminals = nonterminals or set()
    return lex.tokenize_rhs(alt, line_no, nonterminals, GrammarError)


def tokenize_rhs_lex(alt, nonterminals, line_no):
    """Лексически разбирает RHS (публичная обертка для совместимости)."""
    return lex.tokenize_rhs_lex(alt, nonterminals, line_no, GrammarError)

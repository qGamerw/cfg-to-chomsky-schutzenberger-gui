EPSILON_SYMBOLS = {"ε", "epsilon", '""'}
# Символы, которые трактуются как пустая строка (epsilon) при вводе.


class GrammarError(Exception):
    def __init__(self, message, line_no=None):
        self.message = message
        self.line_no = line_no
        super().__init__(self.__str__())

    def __str__(self):
        if self.line_no is None:
            return self.message
        return f"Строка {self.line_no}: {self.message}"


class Grammar:
    def __init__(self, productions, start_symbol):
        self.productions = productions
        self.start_symbol = start_symbol
        # Набор нетерминалов равен ключам словаря продукций.
        self.nonterminals = set(productions.keys())
        # Терминалы вычисляем как все символы RHS, не являющиеся нетерминалами.
        self.terminals = self._collect_terminals()

    def _collect_terminals(self):
        """Собирает терминалы по всем правым частям правил."""
        terminals = set()
        for alts in self.productions.values():
            for alt in alts:
                for symbol in alt:
                    if symbol not in self.nonterminals:
                        terminals.add(symbol)
        return terminals


def parse_grammar(text):
    """Парсит текстовую грамматику в объект Grammar."""
    if not text.strip():
        raise GrammarError("Пустой ввод грамматики.")

    productions = {}
    start_symbol = None

    for idx, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if "->" not in line:
            raise GrammarError("Отсутствует '->' в правиле.", idx)
        lhs, rhs = line.split("->", 1)
        lhs = lhs.strip()
        if not lhs:
            raise GrammarError("Пустая левая часть правила.", idx)

        if start_symbol is None:
            start_symbol = lhs

        alternatives = [alt.strip() for alt in rhs.split("|")]
        if not alternatives:
            raise GrammarError("Отсутствует правая часть правила.", idx)

        parsed_alts = []
        for alt in alternatives:
            if alt in EPSILON_SYMBOLS or alt == "":
                parsed_alts.append([])
                continue
            # Разбираем RHS в список символов (терминалы/нетерминалы).
            symbols = tokenize_rhs(alt, idx)
            parsed_alts.append(symbols)

        productions.setdefault(lhs, []).extend(parsed_alts)

    if start_symbol is None:
        raise GrammarError("Не найден стартовый символ.")

    return Grammar(productions, start_symbol)


def tokenize_rhs(alt, line_no):
    """Разбивает RHS на символы: по пробелам либо по отдельным буквам."""
    if " " in alt:
        parts = [part for part in alt.split() if part]
    else:
        parts = list(alt)

    if not parts:
        raise GrammarError("Пустая правая часть правила.", line_no)

    # Базовая валидация на наличие управляющих символов грамматики.
    for part in parts:
        if "->" in part or "|" in part:
            raise GrammarError("Некорректный символ в правиле.", line_no)
    return parts

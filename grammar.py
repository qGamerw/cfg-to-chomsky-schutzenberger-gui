EPSILON_SYMBOLS = {"ε", "epsilon", '""'}
# Символы, которые трактуются как пустая строка (epsilon) при вводе.

ARROW_SYMBOLS = ("->", "→")


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

    # Сначала считываем строки и собираем все LHS (нетерминалы),
    # затем токенизируем RHS с учетом этого полного набора.
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
                raise GrammarError("Пустая левая часть правила.", idx)

            current_lhs = lhs
            if start_symbol is None:
                start_symbol = lhs

            alternatives = split_alternatives(rhs, idx)
            if not alternatives:
                raise GrammarError("Отсутствует правая часть правила.", idx)

            raw_rules.append((idx, lhs, alternatives))
            productions.setdefault(lhs, [])
            continue

        # Поддержка продолжения RHS на следующей строке:
        #   A -> x
        #      | y
        if line.startswith("|"):
            if current_lhs is None:
                raise GrammarError("Альтернатива '|' без предыдущего правила.", idx)
            rhs_cont = line[1:]
            alternatives = split_alternatives(rhs_cont, idx)
            if not alternatives:
                raise GrammarError("Отсутствует правая часть правила.", idx)
            raw_rules.append((idx, current_lhs, alternatives))
            continue

        raise GrammarError("Отсутствует '->' (или '→') в правиле.", idx)

    if start_symbol is None:
        raise GrammarError("Не найден стартовый символ.")

    nonterminals = set(productions.keys())

    for idx, lhs, alternatives in raw_rules:
        for alt in alternatives:
            if alt in EPSILON_SYMBOLS or alt == "":
                productions[lhs].append([])
                continue
            # Разбираем RHS в список символов (терминалы/нетерминалы).
            symbols = tokenize_rhs(alt, idx, nonterminals)
            productions[lhs].append(symbols)

    return Grammar(productions, start_symbol)


def split_rule_arrow(line, line_no):
    """Делит строку правила по стрелке (поддерживает '->' и '→')."""
    for arrow in ARROW_SYMBOLS:
        if arrow in line:
            return line.split(arrow, 1)
    raise GrammarError("Отсутствует '->' (или '→') в правиле.", line_no)


def split_alternatives(rhs, line_no):
    """Делит RHS по '|', игнорируя '|' внутри двойных кавычек."""
    parts = []
    current = []
    in_quotes = False
    i = 0
    n = len(rhs)

    while i < n:
        ch = rhs[i]
        if ch == '"' and (i == 0 or rhs[i - 1] != "\\"):
            in_quotes = not in_quotes
            current.append(ch)
            i += 1
            continue

        if ch == "|" and not in_quotes:
            parts.append("".join(current).strip())
            current = []
            i += 1
            continue

        current.append(ch)
        i += 1

    if in_quotes:
        raise GrammarError("Незакрытая кавычка в правой части правила.", line_no)

    parts.append("".join(current).strip())
    return parts


def normalize_nonterminal(token):
    """Нормализует нетерминал: <Expr> -> Expr, Expr -> Expr."""
    t = token.strip()
    if len(t) >= 3 and t.startswith("<") and t.endswith(">"):
        inner = t[1:-1].strip()
        if inner:
            return inner
    return t


def tokenize_rhs(alt, line_no, nonterminals=None):
    """Разбивает RHS на корректные токены грамматики."""
    nonterminals = nonterminals or set()

    parts = tokenize_rhs_lex(alt, nonterminals, line_no)

    if not parts:
        raise GrammarError("Пустая правая часть правила.", line_no)

    # Базовая валидация на наличие управляющих символов грамматики.
    for part in parts:
        if "->" in part or "→" in part or "|" in part:
            raise GrammarError("Некорректный символ в правиле.", line_no)
    return parts


def tokenize_rhs_lex(alt, nonterminals, line_no):
    """
    Лексическая токенизация RHS (с пробелами и без):
    - нетерминал: <Name> или Name (если Name есть среди LHS);
    - терминалы-символы: по одному символу (например: P ( ) * + - /);
    - цифры 0..9: отдельные токены;
    - пробелы игнорируются.

    Примеры:
      P(NumProd)         -> ["P", "(", "NumProd", ")"]
      NumFactor*NumProd  -> ["NumFactor", "*", "NumProd"]
    """
    if not alt:
        return []

    nt_list = sorted(nonterminals, key=len, reverse=True)

    def is_ident_start(ch):
        return ch.isalpha() or ch == "_"

    def is_ident_char(ch):
        return ch.isalnum() or ch == "_"

    def has_ident_boundary(end_pos):
        if end_pos >= len(alt):
            return True
        return not is_ident_char(alt[end_pos])

    def match_nonterminal_at(pos):
        for nt in nt_list:
            if alt.startswith(nt, pos):
                # Для идентификаторных NT избегаем частичных совпадений,
                # например Int внутри IntValue.
                if len(nt) > 1 and (nt[0].isalpha() or nt[0] == "_"):
                    if not has_ident_boundary(pos + len(nt)):
                        continue
                return nt
        return None

    tokens = []
    i = 0
    n = len(alt)

    while i < n:
        ch = alt[i]

        if ch.isspace():
            i += 1
            continue

        # Нетерминал в угловых скобках: <Expr>
        if ch == "<":
            j = alt.find(">", i + 1)
            if j == -1:
                tokens.append(ch)
                i += 1
            else:
                token = normalize_nonterminal(alt[i : j + 1])
                tokens.append(token)
                i = j + 1
            continue

        # Терминальный литерал в двойных кавычках: "read_write" -> read_write
        if ch == '"':
            j = i + 1
            literal_chars = []
            while j < n:
                cj = alt[j]
                if cj == "\\" and j + 1 < n and alt[j + 1] in ('"', "\\"):
                    literal_chars.append(alt[j + 1])
                    j += 2
                    continue
                if cj == '"':
                    break
                literal_chars.append(cj)
                j += 1

            if j >= n:
                raise GrammarError("Незакрытая кавычка в правой части правила.", line_no)

            literal = "".join(literal_chars)
            if literal == "":
                # Пустая строка как epsilon поддерживается отдельным случаем alt == '""'.
                raise GrammarError("Пустой литерал в кавычках внутри RHS недопустим.", line_no)

            tokens.append(literal)
            i = j + 1
            continue

        nt = match_nonterminal_at(i)
        if nt is not None:
            tokens.append(nt)
            i += len(nt)
            continue

        if ch.isdigit():
            tokens.append(ch)
            i += 1
            continue

        if is_ident_start(ch):
            j = i + 1
            while j < n and is_ident_char(alt[j]):
                # Если на позиции j начинается известный нетерминал,
                # завершаем текущую терминальную лексему перед ним.
                if match_nonterminal_at(j) is not None:
                    break
                j += 1

            ident = alt[i:j]
            if ident in nonterminals:
                tokens.append(ident)
            else:
                # Терминал-лексема (слово) добавляется как единый токен.
                tokens.append(ident)
            i = j
            continue

        # Пунктуация/операторы как отдельные терминалы.
        tokens.append(ch)
        i += 1

    return tokens

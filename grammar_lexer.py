"""Низкоуровневые лексические функции для токенизации правых частей правил."""


def split_rule_arrow(line, line_no, error_cls, arrow_symbols):
    """Делит строку правила по разрешенным стрелкам."""
    for arrow in arrow_symbols:
        if arrow in line:
            return line.split(arrow, 1)
    raise error_cls(
        "Отсутствует '->' (или '→') в правиле. Ожидается формат: "
        "Нетерминал -> правая_часть.",
        line_no,
    )


def split_alternatives(rhs, line_no, error_cls):
    """Делит RHS по '|' с игнорированием '|' внутри двойных кавычек."""
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
        raise error_cls(
            "Незакрытая кавычка в правой части правила. Проверьте, что каждый литерал "
            "вида \"...\" имеет закрывающую кавычку.",
            line_no,
        )

    parts.append("".join(current).strip())
    return parts


def normalize_nonterminal(token):
    """Нормализует нетерминал: <Expr> -> Expr."""
    t = token.strip()
    if len(t) >= 3 and t.startswith("<") and t.endswith(">"):
        inner = t[1:-1].strip()
        if inner:
            return inner
    return t


def tokenize_rhs(alt, line_no, nonterminals, error_cls):
    """Токенизирует RHS в символы грамматики."""
    parts = tokenize_rhs_lex(alt, nonterminals, line_no, error_cls)
    if not parts:
        raise error_cls(
            "Пустая правая часть правила. После стрелки должна быть хотя бы одна "
            "альтернатива или ε/epsilon/\"\".",
            line_no,
        )

    for part in parts:
        if "->" in part or "→" in part or "|" in part:
            raise error_cls(
                "Некорректный символ в правиле. Проверьте расстановку стрелок и '|' "
                "(внутри токенов они недопустимы).",
                line_no,
            )
    return parts


def tokenize_rhs_lex(alt, nonterminals, line_no, error_cls):
    """Лексически разбирает RHS на нетерминалы и терминалы."""
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
                raise error_cls(
                    "Незакрытая кавычка в правой части правила. Проверьте, что литерал "
                    "\"...\" закрыт перед концом строки.",
                    line_no,
                )

            literal = "".join(literal_chars)
            if literal == "":
                raise error_cls(
                    "Пустой литерал в кавычках внутри RHS недопустим. Для ε используйте "
                    "отдельную альтернативу ε, epsilon или \"\".",
                    line_no,
                )

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
                if match_nonterminal_at(j) is not None:
                    break
                j += 1

            ident = alt[i:j]
            tokens.append(ident)
            i = j
            continue

        tokens.append(ch)
        i += 1

    return tokens

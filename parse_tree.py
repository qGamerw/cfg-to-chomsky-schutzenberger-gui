"""Построение дерева разбора для токенизированной КС-грамматики.

Парсер использует ограниченный рекурсивный поиск с мемоизацией и возвращает
одно успешное дерево разбора для всей входной строки (если оно существует).
"""

EPSILON_DISPLAY = "ε"


class ParseError(Exception):
    """Ошибка, когда дерево разбора для входной строки построить не удалось."""

    def __init__(self, message):
        """Создает объект ошибки разбора.

        Параметры:
            message: Текст ошибки для пользователя.
        """
        super().__init__(message)
        self.message = message


class ParseNode:
    """Узел дерева разбора: символ и список дочерних элементов."""

    def __init__(self, symbol, children=None):
        """Создает узел дерева разбора.

        Параметры:
            symbol: Символ в вершине.
            children: Список дочерних узлов/символов.
        """
        self.symbol = symbol
        self.children = children or []

    def pretty(self, indent=0):
        """Возвращает список строк для отображения дерева с отступами."""
        prefix = "  " * indent
        lines = [f"{prefix}{self.symbol}"]
        for child in self.children:
            if isinstance(child, ParseNode):
                lines.extend(child.pretty(indent + 1))
            else:
                lines.append(f"{prefix}  {child}")
        return lines


def tokenize_input(text):
    """Токенизация входной строки: по пробелам либо по символам."""
    text = text.strip()
    if not text:
        return []
    if " " in text:
        return [part for part in text.split() if part]
    return list(text)


def _segment_text_with_terminals(text, terminals, max_variants=256):
    """Разбивает компактную строку на токены терминалов грамматики."""
    if not text:
        return [[]]

    term_list = sorted({t for t in terminals if t}, key=len, reverse=True)
    memo = {}

    def dfs(pos):
        if pos == len(text):
            return [[]]
        if pos in memo:
            return memo[pos]

        variants = []
        for t in term_list:
            if text.startswith(t, pos):
                suffixes = dfs(pos + len(t))
                for suf in suffixes:
                    variants.append([t] + suf)
                    if len(variants) >= max_variants:
                        memo[pos] = variants
                        return variants

        memo[pos] = variants
        return variants

    return dfs(0)


def _tokenize_input_variants(text, grammar):
    """Возвращает варианты токенизации, чтобы поддержать ввод с пробелами и без."""
    raw = text.strip()
    if not raw:
        return []

    variants = []
    terminals = set(grammar.terminals)

    # 1) Прямой ввод по пробелам (если есть).
    if " " in raw:
        spaced = [part for part in raw.split() if part]
        if spaced:
            variants.append(spaced)

        compact = "".join(spaced)
        # 2) Сегментация компактной строки по терминалам.
        variants.extend(_segment_text_with_terminals(compact, terminals))
        # 3) Фолбэк: посимвольно по компактной строке.
        if compact:
            variants.append(list(compact))
            variants.append([compact])
    else:
        # 1) Сегментация по терминалам.
        variants.extend(_segment_text_with_terminals(raw, terminals))
        # 2) Фолбэки.
        variants.append(list(raw))
        variants.append([raw])

    # Удаляем дубликаты, сохраняя порядок.
    unique = []
    seen = set()
    for v in variants:
        key = tuple(v)
        if key not in seen:
            seen.add(key)
            unique.append(v)
    return unique


def parse_string(grammar, input_text):
    """Пытается построить дерево разбора для input_text по данной грамматике."""
    token_variants = _tokenize_input_variants(input_text, grammar)
    if not token_variants:
        raise ParseError(
            "Пустая входная строка для построения дерева разбора. "
            "Введите строку над терминалами грамматики (например: a a b b или aaaabbbb)."
        )

    for tokens in token_variants:
        # Ограничение глубины поиска, чтобы избежать бесконечного разрастания.
        max_steps = max(80, len(tokens) * 20)
        memo = {}

        def parse_symbol(symbol, position, steps_left):
            """Рекурсивный разбор одного символа грамматики с мемоизацией."""
            if steps_left <= 0:
                return []
            key = (symbol, position, steps_left)
            if key in memo:
                return memo[key]
            results = []
            if symbol in grammar.terminals:
                # Терминал совпадает с текущим токеном.
                if position < len(tokens) and tokens[position] == symbol:
                    results.append((ParseNode(symbol), position + 1))
            elif symbol in grammar.nonterminals:
                # Для нетерминала пробуем все альтернативы RHS.
                for rhs in grammar.productions.get(symbol, []):
                    if not rhs:
                        # Эпсилон-правило.
                        results.append((ParseNode(symbol, [EPSILON_DISPLAY]), position))
                        continue
                    current_nodes = [(ParseNode(symbol, []), position)]
                    for part in rhs:
                        next_nodes = []
                        for node, pos in current_nodes:
                            for child_node, next_pos in parse_symbol(part, pos, steps_left - 1):
                                next_nodes.append(
                                    (ParseNode(symbol, node.children + [child_node]), next_pos)
                                )
                        current_nodes = next_nodes
                    results.extend(current_nodes)
            memo[key] = results
            return results

        parses = parse_symbol(grammar.start_symbol, 0, max_steps)
        for node, pos in parses:
            if pos == len(tokens):
                return node

    terminals_preview = sorted(grammar.terminals)
    if len(terminals_preview) > 16:
        terminals_preview = terminals_preview[:16] + ["..."]
    terms_str = ", ".join(terminals_preview)

    raise ParseError(
        "Не удалось построить дерево разбора для входной строки. "
        "Проверьте соответствие строки правилам грамматики и терминалам. "
        f"Терминалы грамматики: {terms_str}."
    )


def format_parse_tree(node):
    """Преобразует дерево разбора в читаемый текст."""
    return "\n".join(node.pretty())

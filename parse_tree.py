EPSILON_DISPLAY = "ε"

class ParseError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ParseNode:
    """Узел дерева разбора: символ и список дочерних узлов."""
    def __init__(self, symbol, children=None):
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


def parse_string(grammar, input_text):
    """Пытается построить дерево разбора для input_text по данной грамматике."""
    tokens = tokenize_input(input_text)
    if not tokens:
        raise ParseError("Пустая входная строка для построения дерева разбора.")
    # Ограничение глубины поиска, чтобы избежать бесконечного разрастания.
    max_steps = max(50, len(tokens) * 10)
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
    raise ParseError("Не удалось построить дерево разбора для входной строки.")


def format_parse_tree(node):
    """Преобразует дерево разбора в читаемый текст."""
    return "\n".join(node.pretty())

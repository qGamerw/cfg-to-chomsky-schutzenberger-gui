"""Тесты в стиле черного ящика для построения дерева разбора."""

import unittest

from grammar import parse_grammar
from parse_tree import ParseError, parse_string


class ParseTreeApiTests(unittest.TestCase):
    """Проверяет сборку дерева разбора в пользовательских сценариях."""

    def test_parses_lexeme_input_without_spaces(self):
        """Лексемный ввод без пробелов должен разбираться по терминалам grammar."""
        grammar = parse_grammar("Start -> Scope\nScope -> read | read_write")
        node = parse_string(grammar, "read_write")
        self.assertEqual(node.symbol, "Start")

    def test_parses_symbolic_input_with_and_without_spaces(self):
        """Для посимвольной grammar поддерживается оба режима ввода."""
        grammar = parse_grammar("S -> aSBb | aa\nB -> bb")
        node1 = parse_string(grammar, "aaaabbbbbb")
        node2 = parse_string(grammar, "a a a a b b b b b b")
        self.assertEqual(node1.symbol, "S")
        self.assertEqual(node2.symbol, "S")

    def test_empty_input_raises_parse_error(self):
        """Пустая строка для дерева должна давать ParseError."""
        grammar = parse_grammar("S -> a")
        with self.assertRaises(ParseError):
            parse_string(grammar, "   ")


if __name__ == "__main__":
    unittest.main()

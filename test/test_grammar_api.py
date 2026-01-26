"""Тесты в стиле черного ящика для API парсинга грамматики."""

import unittest

from grammar import GrammarError, parse_grammar, split_alternatives


class GrammarApiTests(unittest.TestCase):
    """Проверяет внешнее поведение парсера грамматики."""

    def test_supports_unicode_arrow_and_continuation_lines(self):
        """Парсер принимает стрелку '→' и продолжение RHS через '|'."""
        text = "Start → A B\n      | C\nA -> a\nB -> b\nC -> c"
        grammar = parse_grammar(text)

        self.assertEqual(grammar.start_symbol, "Start")
        self.assertEqual(grammar.productions["Start"], [["A", "B"], ["C"]])

    def test_split_alternatives_ignores_pipe_inside_quotes(self):
        """Символ '|' внутри кавычек не делит альтернативу."""
        rhs = '"a|b" | X | "c|d"'
        parts = split_alternatives(rhs, 1)
        self.assertEqual(parts, ['"a|b"', "X", '"c|d"'])

    def test_quoted_literals_are_terminals_without_quotes(self):
        """Кавычки служебные: терминалом становится только содержимое литерала."""
        grammar = parse_grammar('S -> "read_write" | "admin"')
        self.assertIn("read_write", grammar.terminals)
        self.assertIn("admin", grammar.terminals)
        self.assertNotIn('"', grammar.terminals)

    def test_unclosed_quote_raises_grammar_error(self):
        """Незакрытый литерал в RHS вызывает понятную ошибку."""
        with self.assertRaises(GrammarError) as ctx:
            parse_grammar('S -> "broken')
        self.assertIn("Незакрытая кавычка", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

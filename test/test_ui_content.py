"""Тесты в стиле черного ящика для встроенных текстов и примеров UI."""

import unittest

from grammar import parse_grammar
from ui_content import (
    DEMO_INFO_TEXT,
    EXAMPLE_1_GRAMMAR,
    EXAMPLE_2_GRAMMAR,
    EXAMPLE_3_GRAMMAR,
    EXAMPLE_4_GRAMMAR,
    THEOREM_TEXT,
)


class UIContentTests(unittest.TestCase):
    """Проверяет, что встроенные тексты и примеры валидны."""

    def test_theorem_and_demo_text_are_non_empty(self):
        """Тексты вкладок должны быть заполнены содержанием."""
        self.assertTrue(THEOREM_TEXT.strip())
        self.assertTrue(DEMO_INFO_TEXT.strip())

    def test_all_builtin_example_grammars_parse(self):
        """Все встроенные примеры должны корректно парситься."""
        for text in (EXAMPLE_1_GRAMMAR, EXAMPLE_2_GRAMMAR, EXAMPLE_3_GRAMMAR, EXAMPLE_4_GRAMMAR):
            grammar = parse_grammar(text)
            self.assertTrue(grammar.productions)


if __name__ == "__main__":
    unittest.main()

"""Тесты в стиле черного ящика для форматирования CS-вывода."""

import unittest

from cs_representation import build_cs_representation, format_cs_output, format_cs_output_compact
from grammar import parse_grammar


class CSOutputTests(unittest.TestCase):
    """Проверяет компактный и подробный режимы вывода."""

    def test_compact_output_contains_only_result_sections(self):
        """Компактный вывод не должен содержать секцию подробных шагов."""
        grammar = parse_grammar("S -> a S b | \"\"")
        cs_rep = build_cs_representation(grammar)
        text = format_cs_output_compact(grammar, cs_rep)

        self.assertIn("[SECTION Итого]", text)
        self.assertIn("[SECTION Алфавиты]", text)
        self.assertIn("[SECTION Вывод]", text)
        self.assertIn("[SECTION Формулы]", text)
        self.assertNotIn("[SECTION Steps]", text)
        self.assertIn("Полный список шагов", text)

    def test_detailed_output_contains_steps_and_print_rules(self):
        """Подробный вывод содержит шаги алгоритма и секцию о выводе через h."""
        grammar = parse_grammar("Start -> Scope\nScope -> read | write")
        cs_rep = build_cs_representation(grammar)
        text = format_cs_output(grammar, cs_rep)

        self.assertIn("[SECTION Steps]", text)
        self.assertIn("[SECTION Вывод через h]", text)
        self.assertIn("]read -> read", text)
        self.assertIn("]write -> write", text)


if __name__ == "__main__":
    unittest.main()

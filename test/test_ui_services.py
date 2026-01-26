"""Тесты для сервиса вычислений и кэширования UI."""

import unittest

from grammar import GrammarError
from ui_content import EXAMPLE_1_GRAMMAR
from ui_services import UIComputationService


class UIComputationServiceTests(unittest.TestCase):
    """Проверяет вычислительный pipeline вне Tkinter-виджетов."""

    def test_conversion_result_is_cached_for_same_grammar(self):
        """Повторная конвертация того же текста должна брать результат из кэша."""
        service = UIComputationService()

        first, first_from_cache = service.get_conversion(EXAMPLE_1_GRAMMAR)
        second, second_from_cache = service.get_conversion(EXAMPLE_1_GRAMMAR)

        self.assertTrue(first.ok)
        self.assertFalse(first_from_cache)
        self.assertTrue(second_from_cache)
        self.assertIs(first, second)

    def test_invalid_grammar_error_is_cached(self):
        """Ошибка grammar тоже должна кэшироваться до изменения текста."""
        service = UIComputationService()

        first, first_from_cache = service.get_conversion("S a")
        second, second_from_cache = service.get_conversion("S a")

        self.assertFalse(first.ok)
        self.assertFalse(first_from_cache)
        self.assertTrue(second_from_cache)
        self.assertIn("Отсутствует '->'", first.error)
        self.assertIs(first, second)

    def test_get_grammar_reuses_successful_conversion_cache(self):
        """Построение дерева должно переиспользовать уже разобранную grammar."""
        service = UIComputationService()
        conversion, _ = service.get_conversion(EXAMPLE_1_GRAMMAR)

        grammar, from_cache = service.get_grammar(EXAMPLE_1_GRAMMAR)

        self.assertTrue(from_cache)
        self.assertIs(grammar, conversion.grammar)

    def test_tree_parse_cache_uses_normalized_input(self):
        """Кэш дерева должен считать эквивалентными строки с внешними пробелами."""
        service = UIComputationService()
        grammar, _ = service.get_grammar(EXAMPLE_1_GRAMMAR)

        first, first_from_cache = service.get_tree_parse(grammar, EXAMPLE_1_GRAMMAR, "a a b b")
        second, second_from_cache = service.get_tree_parse(grammar, EXAMPLE_1_GRAMMAR, "  a a b b  ")

        self.assertEqual(first.error, "")
        self.assertFalse(first_from_cache)
        self.assertTrue(second_from_cache)
        self.assertIs(first, second)

    def test_get_grammar_raises_without_successful_cache(self):
        """Если успешного кэша нет, service должен честно пробрасывать GrammarError."""
        service = UIComputationService()

        with self.assertRaises(GrammarError):
            service.get_grammar("S a")


if __name__ == "__main__":
    unittest.main()

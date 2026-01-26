"""Тесты в стиле черного ящика для потока конвертации CFG -> CS."""

import unittest

from cs_representation import build_cs_representation, format_cs_output
from grammar import parse_grammar
from parse_tree import ParseError, parse_string


class ConverterBlackBoxTests(unittest.TestCase):
    """Проверяет наблюдаемое поведение конвертера как "черный ящик"."""

    def test_compact_expr_tokenization_and_expand_step(self):
        """Проверяет корректную токенизацию Expr -> P(NumProd)/P(DenProd)."""
        grammar_text = (
            "Start -> Expr\n"
            "Expr -> P(NumProd) / P(DenProd)\n"
            "NumProd -> NumFactor | NumFactor * NumProd\n"
            "DenProd -> DenFactor | DenFactor * DenProd\n"
            "NumFactor -> ( Int + Int + Int )\n"
            "DenFactor -> ( Int - Int )\n"
            "Int -> Digit | Digit Int\n"
            "Digit -> 0|1|2|3|4|5|6|7|8|9"
        )

        grammar = parse_grammar(grammar_text)
        cs_rep = build_cs_representation(grammar)

        self.assertEqual(
            grammar.productions["Expr"][0],
            ["P", "(", "NumProd", ")", "/", "P", "(", "DenProd", ")"],
        )
        self.assertNotIn("P(NumProd)", cs_rep.stack_symbols)
        self.assertNotIn("P(DenProd)", cs_rep.stack_symbols)
        self.assertIn("P", cs_rep.stack_symbols)

        expected_step = "]Expr [) [DenProd [( [P [/ [) [NumProd [( [P"
        self.assertIn(expected_step, cs_rep.step_regex)

    def test_quoted_literals_are_single_tokens(self):
        """Проверяет, что литералы в кавычках не распадаются и кавычка не попадает в Σ."""
        grammar_text = (
            "Issue -> \"ISSUE(tenant=\" TenantId \",client=\" ClientId \")\"\n"
            "TenantId -> \"t1\"\n"
            "ClientId -> \"c1\""
        )

        grammar = parse_grammar(grammar_text)

        self.assertEqual(
            grammar.productions["Issue"][0],
            ["ISSUE(tenant=", "TenantId", ",client=", "ClientId", ")"],
        )
        self.assertNotIn('"', grammar.terminals)

    def test_scope_lexemes_not_split_to_letters(self):
        """Проверяет, что значения Scope остаются целыми лексемами."""
        grammar_text = (
            "Start -> Scope\n"
            "Scope -> read | write | read_write | admin"
        )

        grammar = parse_grammar(grammar_text)
        cs_rep = build_cs_representation(grammar)

        for lexeme in ("read", "write", "read_write", "admin"):
            self.assertIn(lexeme, grammar.terminals)
            self.assertEqual(cs_rep.homomorphism[f"]{lexeme}"], lexeme)

        for bad in ("a", "c", "d", "e", "i", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "w", "_"):
            self.assertNotIn(bad, grammar.terminals)

    def test_multiline_alternative_parsing(self):
        """Проверяет поддержку продолжения альтернатив на новой строке через |."""
        grammar_text = "Expr -> A B\n      | C\nA -> a\nB -> b\nC -> c"
        grammar = parse_grammar(grammar_text)

        self.assertEqual(grammar.productions["Expr"], [["A", "B"], ["C"]])

    def test_parse_tree_accepts_inputs_with_and_without_spaces(self):
        """Проверяет построение дерева для эквивалентных входов с пробелами и без."""
        grammar = parse_grammar("S -> aSBb | aa\nB -> bb")

        node_no_spaces = parse_string(grammar, "aaaabbbbbb")
        node_with_spaces = parse_string(grammar, "a a a a b b b b b b")

        self.assertEqual(node_no_spaces.symbol, "S")
        self.assertEqual(node_with_spaces.symbol, "S")

    def test_output_section_explains_where_output_appears(self):
        """Проверяет наличие явной секции о выводе через h."""
        grammar = parse_grammar("Start -> Scope\nScope -> read | read_write")
        cs_rep = build_cs_representation(grammar)
        text = format_cs_output(grammar, cs_rep)

        self.assertIn("[SECTION Вывод через h]", text)
        self.assertIn("PRINT = { ]t -> t | t ∈ Σ }", text)
        self.assertIn("]read -> read", text)
        self.assertIn("]read_write -> read_write", text)

    def test_invalid_input_for_parse_tree_raises_error(self):
        """Проверяет, что для неверной строки разбор завершается ParseError."""
        grammar = parse_grammar("S -> a S b | \"\"")
        with self.assertRaises(ParseError):
            parse_string(grammar, "b a")


if __name__ == "__main__":
    unittest.main()

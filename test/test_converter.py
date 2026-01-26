import unittest

from cs_representation import build_cs_representation, format_cs_output
from grammar import GrammarError, parse_grammar, tokenize_rhs
from parse_tree import format_parse_tree, parse_string, ParseError


class GrammarParsingTests(unittest.TestCase):
    def test_parse_basic_rule(self):
        grammar = parse_grammar("S -> a S b | ε")
        self.assertEqual(grammar.start_symbol, "S")
        self.assertEqual(grammar.productions["S"], [["a", "S", "b"], []])
        self.assertIn("a", grammar.terminals)
        self.assertIn("b", grammar.terminals)

    def test_parse_multiple_lines(self):
        grammar = parse_grammar("S -> A B | b\nA -> a A | a\nB -> b B | b")
        self.assertEqual(grammar.start_symbol, "S")
        self.assertEqual(len(grammar.productions["A"]), 2)
        self.assertEqual(len(grammar.productions["B"]), 2)

    def test_parse_error_missing_arrow(self):
        with self.assertRaises(GrammarError) as context:
            parse_grammar("S a S b")
        self.assertIn("'->'", str(context.exception))

    def test_parse_empty_input(self):
        with self.assertRaises(GrammarError) as context:
            parse_grammar("   ")
        self.assertIn("Пустой ввод", str(context.exception))

    def test_parse_empty_lhs(self):
        with self.assertRaises(GrammarError) as context:
            parse_grammar(" -> a")
        self.assertIn("Пустая левая часть", str(context.exception))

    def test_parse_epsilon_alt(self):
        grammar = parse_grammar("S -> ε | a")
        self.assertEqual(grammar.productions["S"], [[], ["a"]])

    def test_parse_spaces_in_rhs(self):
        grammar = parse_grammar("S -> a S b")
        self.assertEqual(grammar.productions["S"], [["a", "S", "b"]])

    def test_tokenize_rhs_split(self):
        tokens = tokenize_rhs("a S b", 1)
        self.assertEqual(tokens, ["a", "S", "b"])


class CSRepresentationTests(unittest.TestCase):
    def test_build_representation_and_format(self):
        grammar = parse_grammar("S -> a S b | ε")
        cs_rep = build_cs_representation(grammar)
        output = format_cs_output(grammar, cs_rep)
        self.assertIn("[SECTION Γ]", output)
        self.assertIn("[SECTION Dyck_Γ]", output)
        self.assertIn("[SECTION R]", output)
        self.assertIn("[SECTION h]", output)
        self.assertIn("R =", output)
        self.assertIn("[SECTION Steps]", output)

    def test_gamma_pairs_include_productions(self):
        grammar = parse_grammar("S -> a | b")
        cs_rep = build_cs_representation(grammar)
        self.assertEqual(len(cs_rep.gamma_pairs), 2)
        self.assertTrue(any(pair[0].startswith("[S") for pair in cs_rep.gamma_pairs))

    def test_homomorphism_prefix_suffix_with_terminal_only(self):
        grammar = parse_grammar("S -> a")
        cs_rep = build_cs_representation(grammar)
        open_bracket, close_bracket, _, _ = cs_rep.gamma_pairs[0]
        self.assertEqual(cs_rep.homomorphism[open_bracket], "\"a\"")
        self.assertEqual(cs_rep.homomorphism[close_bracket], "\"\"")

    def test_homomorphism_prefix_suffix(self):
        grammar = parse_grammar("S -> a S b | T\nT -> c")
        cs_rep = build_cs_representation(grammar)
        self.assertEqual(cs_rep.homomorphism["[S1"], "\"a\"")
        self.assertEqual(cs_rep.homomorphism["]S1"], "\"b\"")
        self.assertEqual(cs_rep.homomorphism["[S2"], "\"\"")
        self.assertEqual(cs_rep.homomorphism["]S2"], "\"\"")
        self.assertEqual(cs_rep.homomorphism["[T1"], "\"c\"")
        self.assertEqual(cs_rep.homomorphism["]T1"], "\"\"")

    def test_r_regex_example(self):
        grammar = parse_grammar("S -> a S b | T\nT -> c T | c")
        cs_rep = build_cs_representation(grammar)
        expected = "([S1)* [S2 ]S2 ([T1)* [T2 ]T2 (]T1)* (]S1)*"
        self.assertEqual(cs_rep.r_regex, expected)

    def test_r_regex_with_b_block(self):
        grammar = parse_grammar("S -> a S B b | aa\nB -> bb")
        cs_rep = build_cs_representation(grammar)
        expected = "([S1)* [S2 ]S2 ([B1 ]B1 ]S1)*"
        self.assertEqual(cs_rep.r_regex, expected)

    def test_homomorphism_for_b_block(self):
        grammar = parse_grammar("S -> a S B b | aa\nB -> bb")
        cs_rep = build_cs_representation(grammar)
        self.assertEqual(cs_rep.homomorphism["[S1"], "\"a\"")
        self.assertEqual(cs_rep.homomorphism["]S1"], "\"b\"")
        self.assertEqual(cs_rep.homomorphism["[S2"], "\"aa\"")
        self.assertEqual(cs_rep.homomorphism["]S2"], "\"\"")
        self.assertEqual(cs_rep.homomorphism["[B1"], "\"bb\"")
        self.assertEqual(cs_rep.homomorphism["]B1"], "\"\"")


class ParseTreeTests(unittest.TestCase):
    def test_parse_tree_for_input(self):
        grammar = parse_grammar("S -> a S b | ε")
        tree = parse_string(grammar, "a a b b")
        tree_text = format_parse_tree(tree)
        self.assertIn("S", tree_text)
        self.assertIn("a", tree_text)
        self.assertIn("b", tree_text)

    def test_parse_tree_empty_input_error(self):
        grammar = parse_grammar("S -> a")
        with self.assertRaises(ParseError) as context:
            parse_string(grammar, "   ")
        self.assertIn("Пустая входная строка", str(context.exception))


if __name__ == "__main__":
    unittest.main()

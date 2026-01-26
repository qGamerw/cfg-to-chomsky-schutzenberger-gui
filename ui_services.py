"""Сервисы вычислений и кэширования для Tkinter UI."""

from dataclasses import dataclass
from typing import Optional

from cs_representation import CSRepresentation, build_cs_representation, format_cs_output, format_cs_output_compact
from grammar import Grammar, GrammarError, parse_grammar
from parse_tree import ParseError, ParseNode, parse_string


@dataclass
class ConversionResult:
    """Результат конвертации грамматики в CS-представление."""

    grammar_text: str
    ok: bool
    error: str = ""
    grammar: Optional[Grammar] = None
    cs_rep: Optional[CSRepresentation] = None
    result_text: str = ""
    detailed_result_text: str = ""


@dataclass
class TreeParseResult:
    """Результат построения дерева для пары grammar + input string."""

    grammar_text: str
    input_string: str
    parse_tree: Optional[ParseNode] = None
    error: str = ""


class UIComputationService:
    """Инкапсулирует вычислительный pipeline и кэши UI."""

    def __init__(self):
        self._conversion_cache: Optional[ConversionResult] = None
        self._tree_parse_cache: Optional[TreeParseResult] = None

    def clear_all(self):
        """Сбрасывает кэш конвертации и дерева разбора."""
        self._conversion_cache = None
        self._tree_parse_cache = None

    def clear_tree_parse(self):
        """Сбрасывает только кэш дерева разбора."""
        self._tree_parse_cache = None

    def get_cached_conversion(self, grammar_text: str, successful_only: bool = False) -> Optional[ConversionResult]:
        """Возвращает кэш конвертации для текста grammar, если он подходит."""
        cached = self._conversion_cache
        if cached is None or cached.grammar_text != grammar_text:
            return None
        if successful_only and not cached.ok:
            return None
        return cached

    def get_grammar(self, grammar_text: str):
        """Возвращает разобранную grammar, по возможности используя кэш конвертации."""
        cached = self.get_cached_conversion(grammar_text, successful_only=True)
        if cached is not None and cached.grammar is not None:
            return cached.grammar, True
        return parse_grammar(grammar_text), False

    def get_conversion(self, grammar_text: str):
        """Возвращает результат конвертации и признак использования кэша."""
        cached = self.get_cached_conversion(grammar_text)
        if cached is not None:
            return cached, True

        self.clear_tree_parse()
        try:
            grammar = parse_grammar(grammar_text)
            cs_rep = build_cs_representation(grammar)
            result = ConversionResult(
                grammar_text=grammar_text,
                ok=True,
                grammar=grammar,
                cs_rep=cs_rep,
                result_text=format_cs_output_compact(grammar, cs_rep),
                detailed_result_text=format_cs_output(grammar, cs_rep, None),
            )
        except GrammarError as exc:
            result = ConversionResult(
                grammar_text=grammar_text,
                ok=False,
                error=str(exc),
            )

        self._conversion_cache = result
        return result, False

    def get_tree_parse(self, grammar: Grammar, grammar_text: str, input_string: str):
        """Возвращает дерево разбора и признак использования кэша."""
        normalized_input = input_string.strip()
        cached = self._tree_parse_cache
        if (
            cached is not None
            and cached.grammar_text == grammar_text
            and cached.input_string == normalized_input
        ):
            return cached, True

        parse_tree = None
        error = ""
        try:
            parse_tree = parse_string(grammar, input_string)
        except ParseError as exc:
            error = exc.message

        result = TreeParseResult(
            grammar_text=grammar_text,
            input_string=normalized_input,
            parse_tree=parse_tree,
            error=error,
        )
        self._tree_parse_cache = result
        return result, False

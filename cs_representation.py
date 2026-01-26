"""Построение компонентов представления Хомского-Шютценбергера для КС-грамматики.

Публичные точки входа:
- ``build_cs_representation``: строит K, Γ, R и h;
- ``format_cs_output_compact``: краткий вывод для пользователя;
- ``format_cs_output``: подробный пошаговый вывод.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

# Как отображается ε (пустая строка) в выводе интерфейса.
EPSILON_DISPLAY = "ε"
BOTTOM_MARKER = "⊥"


@dataclass(frozen=True)
class CSRepresentation:
    """Представление Хомского–Шютценбергера: ``L(G) = h(R ∩ Dyck_Γ)``.

    Реализация использует конструктивную схему через имитацию PDA для CFG:
    - ``K`` — алфавит стека (нетерминалы, терминалы и маркер дна);
    - ``Γ`` — по одной паре скобок на каждый символ из ``K``;
    - ``R`` — регулярное ограничение на локальные шаги PDA;
    - ``Dyck_Γ`` — корректная вложенность/баланс скобок;
    - ``h`` — гомоморфизм (``]t -> t`` для терминалов, остальное в ``ε``).

    Примечание: полученное представление корректно, но не обязательно минимально.
    """

    # Stack alphabet K (for display).
    stack_symbols: List[str]

    # Bracket pairs for Γ: (open, close, stack_symbol)
    gamma_pairs: List[Tuple[str, str, str]]

    # Pretty “regex-like” definitions.
    r_regex: str
    step_regex: str

    # Homomorphism h: Γ* -> Σ*
    homomorphism: Dict[str, str]


def _open(sym: str) -> str:
    """Возвращает открывающую скобку для символа стека."""
    return f"[{sym}"


def _close(sym: str) -> str:
    """Возвращает закрывающую скобку для символа стека."""
    return f"]{sym}"


def _preview(items: List[str], max_items: int = 12) -> str:
    """Возвращает компактное строковое представление списка символов."""
    if len(items) <= max_items:
        return ", ".join(items)
    head = ", ".join(items[:max_items])
    return f"{head}, ... (+{len(items) - max_items})"


def _format_print_rules_lines(terminals: List[str], per_line: int = 6) -> List[str]:
    """Форматирует PRINT-правила в несколько строк для удобного чтения."""
    if not terminals:
        return ["  (терминалы отсутствуют)"]

    rules = [f"]{t} -> {t}" for t in terminals]
    lines: List[str] = []
    for i in range(0, len(rules), per_line):
        lines.append("  " + ", ".join(rules[i : i + per_line]))
    return lines


def _build_stack_alphabet(grammar) -> List[str]:
    """Строит алфавит стека K = N ∪ Σ ∪ {⊥} в стабильном порядке."""
    ordered: List[str] = []

    def add_all(items: List[str]):
        for x in items:
            if x not in ordered:
                ordered.append(x)

    add_all(sorted(grammar.nonterminals))
    add_all(sorted(grammar.terminals))
    add_all([BOTTOM_MARKER])
    return ordered


def build_cs_representation(grammar) -> CSRepresentation:
    """Строит компоненты K, Γ, R и h для произвольной CFG (включая ε-продукции)."""
    # K: stack symbols
    stack_symbols = _build_stack_alphabet(grammar)

    # Γ: one bracket pair per stack symbol
    gamma_pairs = [(_open(s), _close(s), s) for s in stack_symbols]

    # R: regular filter, described via a STEP union
    r_regex, step_regex = build_r_components(grammar)

    # h: homomorphism (close-terminal -> terminal; everything else -> ε)
    homomorphism = build_homomorphism(grammar)

    return CSRepresentation(
        stack_symbols=stack_symbols,
        gamma_pairs=gamma_pairs,
        r_regex=r_regex,
        step_regex=step_regex,
        homomorphism=homomorphism,
    )


def build_homomorphism(grammar) -> Dict[str, str]:
    """Строит гомоморфизм ``h : Γ* -> Σ*``.

    Правила:
    - закрывающая скобка терминала отображается в сам терминал;
    - все остальные скобки отображаются в ``ε``.
    """
    h: Dict[str, str] = {}

    # Terminals: open -> ε, close -> terminal
    for t in sorted(grammar.terminals):
        h[_open(t)] = EPSILON_DISPLAY
        h[_close(t)] = t

    # Nonterminals: both open/close -> ε
    for nt in sorted(grammar.nonterminals):
        h[_open(nt)] = EPSILON_DISPLAY
        h[_close(nt)] = EPSILON_DISPLAY

    # Bottom marker: both open/close -> ε
    h[_open(BOTTOM_MARKER)] = EPSILON_DISPLAY
    h[_close(BOTTOM_MARKER)] = EPSILON_DISPLAY

    return h


def build_r_components(grammar) -> Tuple[str, str]:
    """Строит регулярный фильтр ``R`` и выражение ``STEP``.

    В ``STEP`` добавляются:
    - шаги ``expand`` для всех правил ``A -> α`` (через ``]A`` и открывающие скобки RHS в обратном порядке);
    - шаги ``match`` для всех терминалов ``t`` (в виде ``]t``).

    Итоговая форма фильтра:
    ``R = [⊥ [S (STEP)* ]⊥``.
    """
    start = grammar.start_symbol

    step_alts: List[str] = []

    # (1) expansions for every production
    for lhs, alts in grammar.productions.items():
        for rhs in alts:
            parts = [_close(lhs)]
            for sym in reversed(rhs):
                parts.append(_open(sym))
            step_alts.append(" ".join(parts))

    # (2) terminal matches
    for t in sorted(grammar.terminals):
        step_alts.append(_close(t))

    if not step_alts:
        step_regex = EPSILON_DISPLAY
    else:
        # Parenthesize each alternative for readability.
        step_regex = " | ".join(f"({alt})" for alt in step_alts)

    r_regex = f"{_open(BOTTOM_MARKER)} {_open(start)} (STEP)* {_close(BOTTOM_MARKER)}"
    return r_regex, step_regex


def format_cs_output_compact(grammar, cs_rep: CSRepresentation) -> str:
    """Формирует краткий и понятный отчет для вкладки "Вывод"."""
    lines: List[str] = []
    lines.append("Краткий результат конвертации CFG -> Chomsky–Schützenberger")
    lines.append("L = h(R ∩ Dyck_Γ)")
    lines.append("")

    nonterminals = sorted(grammar.nonterminals)
    terminals = sorted(grammar.terminals)
    expand_count = sum(len(alts) for alts in grammar.productions.values())
    match_count = len(terminals)

    lines.append("[SECTION Итого] Ключевые метрики конвертации")
    lines.append(
        f"Стартовый символ: {grammar.start_symbol} | "
        f"N={len(nonterminals)}, Σ={len(terminals)}, K={len(cs_rep.stack_symbols)}, Γ={len(cs_rep.gamma_pairs)}"
    )
    lines.append(f"Локальные шаги PDA: expand={expand_count}, match={match_count}")
    lines.append("")

    lines.append("[SECTION Алфавиты] Быстрый обзор N, Σ и K")
    lines.append("N = {" + _preview(nonterminals) + "}")
    lines.append("Σ = {" + _preview(terminals) + "}")
    lines.append("K = N ∪ Σ ∪ {⊥}")
    lines.append("")

    lines.append("[SECTION Вывод] Где появляется итоговая строка")
    lines.append("Сначала строятся служебные скобочные слова из (R ∩ Dyck_Γ), это еще не итоговая строка языка.")
    lines.append("Итог появляется после применения h: Output(w) = h(w), где w ∈ (R ∩ Dyck_Γ).")
    lines.append("При этом печатаются только закрывающие скобки терминалов: ]t -> t, остальные символы стираются в ε.")
    lines.append("PRINT:")
    lines.extend(_format_print_rules_lines(terminals, per_line=6))
    lines.append("")

    lines.append("[SECTION Формулы] Компактная форма R и размер STEP")
    lines.append(f"R = {cs_rep.r_regex}")
    step_alts_count = cs_rep.step_regex.count("(")
    lines.append(f"STEP: {step_alts_count} альтернатив")
    lines.append("(Полный список шагов и полное h см. во вкладке 'Подробный вывод')")
    lines.append("")

    return "\n".join(lines)


def format_cs_output(grammar, cs_rep: CSRepresentation, parse_tree_text: str | None = None) -> str:
    """Формирует подробный человекочитаемый отчет с секциями для UI."""
    lines: List[str] = []
    lines.append("Chomsky–Schützenberger representation")
    lines.append("L = h(R ∩ Dyck_Γ)")
    lines.append("")

    lines.append("[SECTION Steps] Пошаговая схема построения представления")
    lines.append("1) Строим алфавит стека K = N ∪ Σ ∪ {⊥}.")
    lines.append("2) Строим Γ = {[X, ]X | X ∈ K} (по паре скобок на каждый символ стека).")
    lines.append("3) Строим регулярный фильтр R как множество допустимых локальных шагов CFG→PDA (expansion/match).")
    lines.append("4) Пересекаем R с Dyck_Γ (Dyck гарантирует дисциплину стека: вложенность и совпадение типов).")
    lines.append("5) Применяем гомоморфизм h: ]t -> t для терминалов t, остальные скобки -> ε.")
    lines.append("")

    lines.append("[SECTION K] Алфавит стека")
    lines.append("Алфавит стека K (нетерминалы, терминалы, ⊥):")
    lines.append("K = {" + ", ".join(cs_rep.stack_symbols) + "}")
    lines.append("")

    lines.append("[SECTION Γ] Скобочный алфавит")
    lines.append("Скобочный алфавит Γ (по паре на символ стека):")
    for open_b, close_b, sym in cs_rep.gamma_pairs:
        lines.append(f"- {open_b} ... {close_b}   (для символа стека {sym})")
    lines.append("")

    lines.append("[SECTION Dyck_Γ] Ограничение корректной вложенности")
    lines.append("Dyck_Γ — множество корректно вложенных и сбалансированных скобочных слов над Γ.")
    lines.append("")

    lines.append("[SECTION R] Регулярный фильтр локальных шагов")
    lines.append("Регулярный фильтр R ⊆ Γ* (regex-подобная запись):")
    lines.append(f"STEP = {cs_rep.step_regex}")
    lines.append(f"R = {cs_rep.r_regex}")
    lines.append("")

    lines.append("[SECTION Вывод через h] Как из служебного слова получается результат")
    lines.append("Вывод появляется только после применения h к скобочному слову w ∈ (R ∩ Dyck_Γ).")
    lines.append("Формально: Output(w) = concat(h(]t)) по всем встреченным ]t, где t ∈ Σ.")
    lines.append("PRINT = { ]t -> t | t ∈ Σ }")
    lines.append("Печатающие правила:")
    for t in sorted(grammar.terminals):
        lines.append(f"  ]{t} -> {t}")
    lines.append("Все остальные скобки (включая нетерминалы и ⊥) отображаются в ε.")
    lines.append("")

    lines.append("Расшифровка STEP (локальные шаги PDA):")
    for lhs in sorted(grammar.productions.keys()):
        for rhs in grammar.productions[lhs]:
            rhs_str = " ".join(rhs) if rhs else EPSILON_DISPLAY
            step = " ".join([_close(lhs)] + [_open(s) for s in reversed(rhs)])
            lines.append(f"  - expand: {lhs} -> {rhs_str}   ==>   {step}")
    for t in sorted(grammar.terminals):
        lines.append(f"  - match : {t}   ==>   {_close(t)}")
    lines.append("")

    lines.append("[SECTION h] Полный гомоморфизм Γ* -> Σ*")
    lines.append("Гомоморфизм h: Γ* -> Σ*")
    for symbol in sorted(cs_rep.homomorphism.keys()):
        lines.append(f"  {symbol} -> {cs_rep.homomorphism[symbol]}")

    if parse_tree_text:
        lines.append("")
        lines.append("[SECTION Parse Tree] Текстовая форма дерева разбора")
        lines.append("Дерево разбора для входной строки:")
        lines.append(parse_tree_text)

    return "\n".join(lines)

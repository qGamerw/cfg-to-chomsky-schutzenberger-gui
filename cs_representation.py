from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

# How we display ε (empty string) in the UI output.
EPSILON_DISPLAY = "ε"
BOTTOM_MARKER = "⊥"


@dataclass(frozen=True)
class CSRepresentation:
    """
    Chomsky–Schützenberger representation:
      L(G) = h(R ∩ Dyck_Γ)

    This implementation follows the constructive proof via a PDA simulation of a CFG:
    - K is the stack alphabet (nonterminals, terminals, and a bottom marker).
    - Γ contains one bracket pair per stack symbol (i.e., per symbol of K).
    - R is a regular language describing valid *local* PDA steps (expansions and terminal matches).
    - Dyck_Γ enforces correct stack discipline (well‑nested, type‑correct push/pop).
    - h maps bracket symbols to terminals (close‑terminal -> terminal, everything else -> ε).

    NOTE: The produced CS representation is correct but not necessarily minimal.
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
    return f"[{sym}"


def _close(sym: str) -> str:
    return f"]{sym}"


def _build_stack_alphabet(grammar) -> List[str]:
    """K = N ∪ Σ ∪ {⊥} (display-friendly, stable order)."""
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
    """Build K, Γ, R, h for an arbitrary CFG (including ε-productions)."""
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
    """
    h : Γ* -> Σ*
    - close-terminal maps to that terminal
    - everything else maps to ε
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
    """
    Regular filter R ⊆ Γ*.

    We encode the standard CFG->PDA simulation as a *regular* constraint over bracket symbols:

    - Start: push bottom marker and start symbol
        [⊥ [S

    - Loop step options (STEP):
        (1) Expand nonterminal A using a production A -> X1 X2 ... Xk
            pop A, push Xk ... X2 X1   (reverse, so X1 is processed first)
            ]A [Xk [X{k-1} ... [X1

            For ε-production (k=0): just ]A

        (2) Match a terminal a on stack with next input symbol
            pop a
            ]a

    - Accept: pop bottom marker
        ]⊥

    Then:
        R = [⊥ [S (STEP)* ]⊥

    Dyck_Γ enforces that all pushes/pops are well‑nested and type‑correct.
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


def format_cs_output(grammar, cs_rep: CSRepresentation, parse_tree_text: str | None = None) -> str:
    """Human-readable, sectioned output for the UI."""
    lines: List[str] = []
    lines.append("Chomsky–Schützenberger representation")
    lines.append("L = h(R ∩ Dyck_Γ)")
    lines.append("")

    lines.append("[SECTION Steps]")
    lines.append("1) Строим алфавит стека K = N ∪ Σ ∪ {⊥}.")
    lines.append("2) Строим Γ = {[X, ]X | X ∈ K} (по паре скобок на каждый символ стека).")
    lines.append("3) Строим регулярный фильтр R как множество допустимых локальных шагов CFG→PDA (expansion/match).")
    lines.append("4) Пересекаем R с Dyck_Γ (Dyck гарантирует дисциплину стека: вложенность и совпадение типов).")
    lines.append("5) Применяем гомоморфизм h: ]t -> t для терминалов t, остальные скобки -> ε.")
    lines.append("")

    lines.append("[SECTION K]")
    lines.append("Алфавит стека K (нетерминалы, терминалы, ⊥):")
    lines.append("K = {" + ", ".join(cs_rep.stack_symbols) + "}")
    lines.append("")

    lines.append("[SECTION Γ]")
    lines.append("Скобочный алфавит Γ (по паре на символ стека):")
    for open_b, close_b, sym in cs_rep.gamma_pairs:
        lines.append(f"- {open_b} ... {close_b}   (для символа стека {sym})")
    lines.append("")

    lines.append("[SECTION Dyck_Γ]")
    lines.append("Dyck_Γ — множество корректно вложенных и сбалансированных скобочных слов над Γ.")
    lines.append("")

    lines.append("[SECTION R]")
    lines.append("Регулярный фильтр R ⊆ Γ* (regex-подобная запись):")
    lines.append(f"STEP = {cs_rep.step_regex}")
    lines.append(f"R = {cs_rep.r_regex}")
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

    lines.append("[SECTION h]")
    lines.append("Гомоморфизм h: Γ* -> Σ*")
    for symbol in sorted(cs_rep.homomorphism.keys()):
        lines.append(f"  {symbol} -> {cs_rep.homomorphism[symbol]}")

    if parse_tree_text:
        lines.append("")
        lines.append("[SECTION Parse Tree]")
        lines.append("Дерево разбора для входной строки:")
        lines.append(parse_tree_text)

    return "\n".join(lines)

"""Вспомогательные функции рендера дерева разбора на Canvas."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

from parse_tree import ParseNode


def clear_tree_canvas(
    canvas: tk.Canvas,
    io_font,
    canvas_font,
    zoom: float,
    message: str = "",
):
    """Очищает Canvas и при необходимости показывает подсказку."""
    canvas.delete("all")
    if message:
        base_size = int(io_font.cget("size"))
        zoom_size = max(6, int(round(base_size * zoom)))
        canvas_font.configure(size=zoom_size)
        canvas.create_text(
            16,
            16,
            text=message,
            anchor="nw",
            font=canvas_font,
            fill="#334155",
        )
    bbox = canvas.bbox("all")
    canvas.configure(scrollregion=bbox if bbox else (0, 0, 1, 1))


@dataclass
class _VisNode:
    """Внутренний узел для раскладки и отрисовки дерева."""

    label: str
    children: list["_VisNode"]
    x: float = 0.0
    y: float = 0.0
    depth: int = 0


def _normalize_node(node) -> _VisNode:
    """Преобразует ParseNode в структуру, удобную для рендера."""
    if isinstance(node, ParseNode):
        children: list[_VisNode] = []
        for child in node.children:
            children.append(_normalize_node(child))
        return _VisNode(str(node.symbol), children)
    return _VisNode(str(node), [])


def render_parse_tree(canvas: tk.Canvas, root_node, io_font, canvas_font, zoom: float):
    """Рисует дерево разбора в виде связанных круговых узлов."""
    canvas.delete("all")

    vis_root = _normalize_node(root_node)

    nodes: list[_VisNode] = []

    def collect(n: _VisNode):
        nodes.append(n)
        for c in n.children:
            collect(c)

    collect(vis_root)

    base_size = int(io_font.cget("size"))
    zoom_size = max(6, int(round(base_size * zoom)))
    canvas_font.configure(size=zoom_size)

    max_text_w = 0
    for n in nodes:
        w = int(canvas_font.measure(n.label))
        if w > max_text_w:
            max_text_w = w

    radius = max(int(12 * zoom), int(max_text_w / 2) + int(10 * zoom))
    diameter = 2 * radius

    h_gap = max(radius + int(20 * zoom), int(28 * zoom))
    v_gap = max(2 * radius + int(54 * zoom), int(82 * zoom))
    margin_x = radius + int(24 * zoom)
    margin_y = radius + int(24 * zoom)

    width_memo: dict[int, float] = {}

    def subtree_width(n: _VisNode) -> float:
        key = id(n)
        if key in width_memo:
            return width_memo[key]

        if not n.children:
            width = float(diameter)
        else:
            kids_w = sum(subtree_width(c) for c in n.children)
            kids_w += h_gap * (len(n.children) - 1)
            width = float(max(diameter, kids_w))

        width_memo[key] = width
        return width

    def assign_positions(n: _VisNode, left: float, depth: int):
        n.depth = depth
        n.y = float(depth)

        w = subtree_width(n)
        if not n.children:
            n.x = left + w / 2
            return

        kids_widths = [subtree_width(c) for c in n.children]
        kids_span = sum(kids_widths) + h_gap * (len(kids_widths) - 1)
        cur_left = left + (w - kids_span) / 2
        child_centers: list[float] = []
        for c, cw in zip(n.children, kids_widths):
            assign_positions(c, cur_left, depth + 1)
            child_centers.append(c.x)
            cur_left += cw + h_gap

        n.x = (min(child_centers) + max(child_centers)) / 2

    assign_positions(vis_root, 0.0, 0)

    leaf_nodes = [n for n in nodes if not n.children]
    max_leaf_depth = max((n.depth for n in leaf_nodes), default=0)
    for n in nodes:
        if not n.children:
            n.y = float(max_leaf_depth)
        else:
            n.y = float(n.depth)

    def to_px(n: _VisNode):
        return (margin_x + n.x, margin_y + n.y * v_gap)

    def draw_edges(n: _VisNode):
        x0, y0 = to_px(n)
        for c in n.children:
            x1, y1 = to_px(c)
            canvas.create_line(
                x0,
                y0 + radius,
                x1,
                y1 - radius,
                fill="#334155",
                width=max(1.0, 1.2 * zoom),
            )
            draw_edges(c)

    draw_edges(vis_root)

    for n in nodes:
        x, y = to_px(n)
        is_leaf = not n.children
        fill = "#ffffff" if is_leaf else "#f1f5f9"
        canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            outline="#0f172a",
            width=max(1.0, 1.2 * zoom),
            fill=fill,
        )
        canvas.create_text(x, y, text=n.label, font=canvas_font, fill="#0f172a")

    bbox = canvas.bbox("all")
    if bbox:
        x0, y0, x1, y1 = bbox
        pad = 20
        canvas.configure(scrollregion=(x0 - pad, y0 - pad, x1 + pad, y1 + pad))
    else:
        canvas.configure(scrollregion=(0, 0, 1, 1))

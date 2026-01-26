"""Тесты в стиле черного ящика для рендера дерева на Canvas."""

import tkinter as tk
import tkinter.font as tkfont
import unittest

from parse_tree import ParseNode
from ui_tree_canvas import clear_tree_canvas, render_parse_tree


class UITreeCanvasTests(unittest.TestCase):
    """Проверяет, что дерево и сообщения реально рисуются на Canvas."""

    def test_render_and_clear_canvas(self):
        """После рендера должны быть элементы, после clear с сообщением тоже."""
        root = tk.Tk()
        try:
            canvas = tk.Canvas(root, width=400, height=300)
            canvas.pack()
            font = tkfont.nametofont("TkFixedFont").copy()
            canvas_font = font.copy()

            tree = ParseNode("S", [ParseNode("a"), ParseNode("S", [ParseNode("ε")]), ParseNode("b")])
            render_parse_tree(canvas, tree, font, canvas_font, 1.0)
            root.update_idletasks()
            self.assertIsNotNone(canvas.bbox("all"))

            clear_tree_canvas(canvas, font, canvas_font, 1.0, "hello")
            root.update_idletasks()
            self.assertIsNotNone(canvas.bbox("all"))
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()

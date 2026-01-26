"""Тесты в стиле черного ящика для базовой связки компонентов Tkinter UI."""

import tkinter as tk
import unittest

from ui import CSConverterApp


class UIAppTests(unittest.TestCase):
    """Проверяет пользовательские сценарии верхнего уровня в UI."""

    def test_tabs_and_convert_outputs(self):
        """Интерфейс должен иметь ключевые вкладки и два режима вывода."""
        root = tk.Tk()
        try:
            app = CSConverterApp(root)
            root.update_idletasks()

            tab_ids = app.notebook.tabs()
            tab_texts = [app.notebook.tab(tid, "text") for tid in tab_ids]
            self.assertIn("Вывод", tab_texts)
            self.assertIn("Подробный вывод", tab_texts)
            self.assertIn("Логи", tab_texts)

            app.load_example1()
            app.convert()
            root.update_idletasks()

            compact = app.output_text.get("1.0", "end-1c")
            detailed = app.output_detailed_text.get("1.0", "end-1c")
            logs = app.logs_text.get("1.0", "end-1c")

            self.assertIn("[SECTION Итого]", compact)
            self.assertNotIn("[SECTION Steps]", compact)
            self.assertIn("[SECTION Steps]", detailed)
            self.assertIn("[Конвертация] Результат", logs)
        finally:
            root.destroy()

    def test_convert_uses_cache_when_grammar_unchanged(self):
        """Повторная конвертация без изменений grammar должна использовать кэш."""
        root = tk.Tk()
        try:
            app = CSConverterApp(root)
            app.load_example1()
            app.convert(source="первый запуск")
            root.update_idletasks()

            before = app.logs_text.get("1.0", "end-1c")
            app.convert(source="повтор")
            root.update_idletasks()
            after = app.logs_text.get("1.0", "end-1c")
            delta = after[len(before):]

            self.assertIn("[Конвертация] Использован кэш (грамматика без изменений)", delta)
            self.assertNotIn("[Конвертация] Шаг 1/4: парсинг грамматики", delta)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()

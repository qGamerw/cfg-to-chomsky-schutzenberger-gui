"""Тесты в стиле черного ящика для базовой связки компонентов Tkinter UI."""

import tkinter as tk
import unittest
from unittest import mock

from ui import CSConverterApp


class UIAppTests(unittest.TestCase):
    """Проверяет пользовательские сценарии верхнего уровня в UI."""

    def create_app(self):
        """Создает приложение Tk и регистрирует корректную очистку ресурсов."""
        root = tk.Tk()
        app = CSConverterApp(root)
        self.addCleanup(self.destroy_app, app)
        root.update()
        return root, app

    def destroy_app(self, app):
        """Останавливает фоновые ресурсы приложения и закрывает окно."""
        try:
            if app.root.winfo_exists():
                app._on_close_request()
        except tk.TclError:
            pass

    def read_text(self, widget):
        """Читает содержимое текстового виджета без завершающего переноса."""
        return widget.get("1.0", "end-1c")

    def test_tabs_and_convert_outputs(self):
        """Интерфейс должен иметь ключевые вкладки и два режима вывода."""
        root, app = self.create_app()

        tab_ids = app.notebook.tabs()
        tab_texts = [app.notebook.tab(tid, "text") for tid in tab_ids]
        self.assertIn("Вывод", tab_texts)
        self.assertIn("Подробный вывод", tab_texts)
        self.assertIn("Логи", tab_texts)

        app.load_example1()
        app.convert()
        root.update()

        compact = self.read_text(app.output_text)
        detailed = self.read_text(app.output_detailed_text)
        logs = self.read_text(app.logs_text)

        self.assertIn("[SECTION Итого]", compact)
        self.assertNotIn("[SECTION Steps]", compact)
        self.assertIn("[SECTION Steps]", detailed)
        self.assertIn("[Конвертация] Результат", logs)

    def test_convert_uses_cache_when_grammar_unchanged(self):
        """Повторная конвертация без изменений grammar должна использовать кэш."""
        root, app = self.create_app()
        app.load_example1()
        app.convert(source="первый запуск")
        root.update()

        before = self.read_text(app.logs_text)
        app.convert(source="повтор")
        root.update()
        after = self.read_text(app.logs_text)
        delta = after[len(before):]

        self.assertIn("[Конвертация] Использован кэш (грамматика без изменений)", delta)
        self.assertNotIn("[Конвертация] Шаг 1/4: парсинг грамматики", delta)

    def test_opening_output_tab_autoconverts_grammar(self):
        """Переход на вкладку вывода должен запускать авто-конвертацию."""
        root, app = self.create_app()
        app.load_example1()

        app.notebook.select(app.tab_output_detailed)
        root.update()

        detailed = self.read_text(app.output_detailed_text)
        logs = self.read_text(app.logs_text)

        self.assertIn("[SECTION Steps]", detailed)
        self.assertIn("[Конвертация] Запуск (авто: вкладка Подробный вывод)", logs)

    def test_invalid_grammar_shows_error_and_reuses_error_cache(self):
        """Некорректная grammar должна показывать ошибку и кешироваться до изменения текста."""
        root, app = self.create_app()
        app._set_input("S a")
        app.input_string_var.set("a")

        app.convert(source="ошибка grammar")
        root.update()

        error_text = app.error_label.cget("text")
        self.assertIn("Отсутствует '->'", error_text)
        self.assertEqual(self.read_text(app.output_text), "")
        self.assertEqual(app.detailed_error_label.cget("text"), error_text)
        self.assertEqual(app.tree_error_label.cget("text"), error_text)

        before = self.read_text(app.logs_text)
        app.convert(source="повтор ошибки")
        root.update()
        after = self.read_text(app.logs_text)
        delta = after[len(before):]

        self.assertIn("[Конвертация] Использован кэш ошибки (грамматика не изменялась)", delta)
        self.assertNotIn("[Конвертация] Шаг 1/4: парсинг грамматики", delta)

    def test_build_parse_tree_renders_canvas_and_uses_cache(self):
        """Повторное построение дерева для той же строки должно брать результат из кэша."""
        root, app = self.create_app()
        app.load_example1()

        app.build_parse_tree()
        root.update()

        self.assertEqual(app.tree_error_label.cget("text"), "")
        self.assertIsNotNone(app.tree_canvas.bbox("all"))
        self.assertGreater(len(app.tree_canvas.find_all()), 0)

        before = self.read_text(app.logs_text)
        app.build_parse_tree()
        root.update()
        after = self.read_text(app.logs_text)
        delta = after[len(before):]

        self.assertIn("[Построить дерево] Использован кэш дерева разбора", delta)

    def test_convert_shows_analysis_text_before_new_result(self):
        """При новом анализе вкладки вывода должны сначала показать временный текст."""
        root, app = self.create_app()
        app._show_conversion_in_progress()

        self.assertIn("Идет процесс анализа КСГ", self.read_text(app.output_text))
        self.assertIn("Идет процесс анализа КСГ", self.read_text(app.output_detailed_text))

        app.load_example1()
        with mock.patch.object(app, "_show_conversion_in_progress", wraps=app._show_conversion_in_progress) as show_loading:
            app.convert(source="новый анализ")
            root.update()

        show_loading.assert_called_once()
        self.assertIn("[SECTION Итого]", self.read_text(app.output_text))
        self.assertIn("[SECTION Steps]", self.read_text(app.output_detailed_text))

    def test_copy_output_to_clipboard_logs_action(self):
        """Кнопка копирования должна класть текст в буфер обмена и писать в лог."""
        root, app = self.create_app()
        app.load_example1()
        app.convert()
        root.update()

        with mock.patch.object(app.root, "clipboard_clear") as clipboard_clear, mock.patch.object(
            app.root,
            "clipboard_append",
        ) as clipboard_append:
            app._copy_text_widget_contents(app.output_text, "краткий вывод")

        clipboard_clear.assert_called_once_with()
        clipboard_append.assert_called_once()
        copied_text = clipboard_append.call_args.args[0]
        self.assertIn("[SECTION Итого]", copied_text)
        self.assertIn("[Буфер обмена] Скопировано: краткий вывод", self.read_text(app.logs_text))

    def test_additional_examples_can_be_loaded(self):
        """Новые учебные примеры должны подставляться в поля ввода."""
        _root, app = self.create_app()

        app.load_example5()
        self.assertIn("( S ) S", self.read_text(app.input_text))
        self.assertEqual(app.input_string_var.get(), "()()")

        app.load_example6()
        self.assertIn("List -> Item | Item , List", self.read_text(app.input_text))
        self.assertEqual(app.input_string_var.get(), "x,y,z")

        app.load_example7()
        self.assertIn('Greeting -> "hello" | "hi"', self.read_text(app.input_text))
        self.assertEqual(app.input_string_var.get(), "hello world")

        app.load_example8()
        self.assertIn("Expr -> Term | Term + Expr", self.read_text(app.input_text))
        self.assertEqual(app.input_string_var.get(), "n+n*n")

    def test_input_tab_buttons_follow_requested_two_row_order(self):
        """На вкладке ввода кнопки должны идти в точном порядке по двум строкам."""
        _root, app = self.create_app()

        def collect_widgets(widget):
            items = []
            for child in widget.winfo_children():
                items.append(child)
                items.extend(collect_widgets(child))
            return items

        all_widgets = collect_widgets(app.tab_input)
        buttons = [
            widget
            for widget in all_widgets
            if isinstance(widget, tk.Widget)
            and str(widget.winfo_class()) == "TButton"
            and widget.cget("text")
            in {
                "Конвертировать",
                "Построить дерево",
                "Загрузить КСГ",
                "Сохранить КСГ",
                "Пример 1",
                "Пример 2",
                "Пример 3",
                "Пример 4",
                "Пример 5",
                "Пример 6",
                "Пример 7",
                "Пример 8",
            }
        ]
        buttons_by_text = {button.cget("text"): button for button in buttons}

        expected_positions = {
            "Конвертировать": (0, 0),
            "Загрузить КСГ": (0, 1),
            "Пример 1": (0, 2),
            "Пример 3": (0, 3),
            "Пример 5": (0, 4),
            "Пример 7": (0, 5),
            "Построить дерево": (1, 0),
            "Сохранить КСГ": (1, 1),
            "Пример 2": (1, 2),
            "Пример 4": (1, 3),
            "Пример 6": (1, 4),
            "Пример 8": (1, 5),
        }

        self.assertEqual(set(buttons_by_text), set(expected_positions))
        for label, (row, column) in expected_positions.items():
            self.assertEqual(int(buttons_by_text[label].grid_info()["row"]), row)
            self.assertEqual(int(buttons_by_text[label].grid_info()["column"]), column)

    def test_demo_has_expected_steps_and_larger_popup_geometry(self):
        """Демо должно содержать все ключевые шаги и увеличенное окно подсказки."""
        _root, app = self.create_app()

        steps = app._build_demo_steps()
        names = [step["name"] for step in steps]
        geometry = app._get_demo_popup_geometry()
        size_part = geometry.split("+", 1)[0]
        width, height = [int(value) for value in size_part.split("x")]

        self.assertEqual(
            names,
            [
                "Ввод грамматики",
                "Вывод",
                "Подробный вывод",
                "Построить дерево",
                "Описание теоремы",
                "Примеры",
                "Настройки",
                "Логи",
            ],
        )
        self.assertGreaterEqual(width, 760)
        self.assertGreaterEqual(height, 620)

    def test_reset_window_geometry_restores_launch_size(self):
        """Кнопка сброса должна возвращать окно к стартовому размеру."""
        root, app = self.create_app()

        root.geometry("1280x860")
        root.update()

        app._reset_window_geometry()
        root.update()

        self.assertEqual(root.winfo_width(), 1000)
        self.assertEqual(root.winfo_height(), 720)
        self.assertIn("[Настройки] Размер окна сброшен: 1000x720", self.read_text(app.logs_text))


if __name__ == "__main__":
    unittest.main()

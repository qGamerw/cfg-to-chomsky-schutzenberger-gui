"""Тесты в стиле черного ящика для точки входа приложения."""

import unittest
from unittest import mock

import main


class MainEntryTests(unittest.TestCase):
    """Проверяет интеграционное поведение функции main()."""

    @mock.patch("main.CSConverterApp")
    @mock.patch("main.tk.Tk")
    def test_main_creates_root_app_and_starts_loop(self, tk_cls, app_cls):
        """Функция main() должна создать root, приложение и вызвать mainloop()."""
        root = mock.Mock()
        tk_cls.return_value = root

        main.main()

        tk_cls.assert_called_once_with()
        app_cls.assert_called_once_with(root)
        root.mainloop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

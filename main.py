"""Точка входа приложения с графическим интерфейсом Tkinter."""

import tkinter as tk

from ui import CSConverterApp


def main():
    """Создает корневое окно Tk и запускает цикл событий."""
    root = tk.Tk()
    CSConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

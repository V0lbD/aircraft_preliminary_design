import sys
from pathlib import Path

# Пути для импортов
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from config import WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT

# Проверяем зависимости
try:
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow
except ImportError as e:
    print(f"ОШИБКА: Отсутствует зависимость - {e}")
    print("Установите зависимости: pip install -r requirements.txt")
    sys.exit(1)


def main():
    """Главная функция приложения"""

    print("=" * 70)
    print("Запуск приложения: Расчёт характеристик летательного аппарата")
    print("=" * 70)

    # Создаём Qt приложение
    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)

    # Создаём главное окно
    window = MainWindow()
    window.show()

    print("Инициализация успешна")
    print(f"Размер окна: {WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    print("UI загружено и готово к работе")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

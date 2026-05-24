"""
Модуль для загрузки и сохранения данных в .txt файлы
Поддерживает русские названия параметров
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import fields, is_dataclass
import sys

# Добавляем путь к основному проекту
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.data_models import (
    ProjectData, EngineTypeEnum, WingFlapsTypeEnum, AircraftTypeEnum, WingChemeEnum
)
from .constants import FIELD_LABELS, FIELD_UNITS, INPUT_FIELDS, OUTPUT_FIELDS


class FileIO:
    """Класс для работы с файлами ввода-вывода"""

    @staticmethod
    def parse_input_file(filepath: Path) -> ProjectData:
        """
        Парсит входной файл и заполняет ProjectData

        Формат файла:
        Посадочное расстояние = 1500
        Тип двигателя = TURBOJET
        Взлётное расстояние = 2000
        ...

        Args:
            filepath: путь к файлу

        Returns:
            ProjectData с заполненными входными данными
        """
        data = ProjectData()

        if not filepath.exists():
            raise FileNotFoundError(f"Файл не найден: {filepath}")

        # Читаем файл построчно
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue

                # Парсим строку вида "Название = значение"
                if '=' not in line:
                    continue

                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Пробуем найти поле по русскому названию
                field_name = FileIO._find_field_by_russian_name(key)

                if field_name is None:
                    # Может быть, это уже английское имя?
                    field_name = key

                # Пробуем установить значение
                FileIO._set_field_value(data, field_name, value)

        # ✅ ВАЖНО: Копируем engine_type из landing_data в takeoff_data
        if data.landing_data.engine_type and not data.takeoff_data.engine_type:
            data.takeoff_data.engine_type = data.landing_data.engine_type

        # ✅ ВАЖНО: Копируем wing_flaps_type из landing_data в takeoff_data
        if data.landing_data.wing_flaps_type and not data.takeoff_data.wing_flaps_type:
            data.takeoff_data.wing_flaps_type = data.landing_data.wing_flaps_type

        return data

    @staticmethod
    def save_output_file(filepath: Path, data: ProjectData) -> None:
        """
        Сохраняет результаты расчётов в .txt файл

        Args:
            filepath: путь к файлу для сохранения
            data: ProjectData с результатами
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("РЕЗУЛЬТАТЫ РАСЧЁТА ДИАГРАММЫ СОГЛАСОВАНИЯ\n")
            f.write("=" * 70 + "\n\n")

            # Входные данные
            f.write("ВХОДНЫЕ ДАННЫЕ\n")
            f.write("-" * 70 + "\n")
            for field_name in INPUT_FIELDS:
                value = FileIO._get_field_value(data, field_name)
                if value is not None:
                    russian_name = FIELD_LABELS.get(field_name, field_name)
                    unit = FIELD_UNITS.get(field_name, "")
                    unit_str = f" ({unit})" if unit else ""
                    f.write(f"{russian_name}{unit_str} = {value}\n")

            f.write("\n")

            # Выходные данные
            f.write("РЕЗУЛЬТАТЫ РАСЧЁТОВ\n")
            f.write("-" * 70 + "\n")
            for field_name in OUTPUT_FIELDS:
                value = FileIO._get_field_value(data, field_name)
                if value is not None:
                    russian_name = FIELD_LABELS.get(field_name, field_name)
                    unit = FIELD_UNITS.get(field_name, "")
                    unit_str = f" ({unit})" if unit else ""

                    # Форматируем значение в зависимости от типа
                    if isinstance(value, float):
                        if value > 1:
                            formatted_value = f"{value:.2f}"
                        else:
                            formatted_value = f"{value:.6f}"
                    else:
                        formatted_value = str(value)

                    f.write(f"{russian_name}{unit_str} = {formatted_value}\n")

            f.write("\n" + "=" * 70 + "\n")

    @staticmethod
    def save_geometry_file(filepath: Path, data: ProjectData) -> None:
        """
        Сохраняет геометрические параметры в строгом формате (как в geom.txt)

        Args:
            filepath: путь к файлу для сохранения
            data: ProjectData с результатами
        """
        geometry = data.geometry_data

        # Вспомогательная функция для форматирования чисел
        def format_value(value: Optional[float]) -> str:
            if value is None:
                return "0.0"
            # Форматируем с 3 знаками после запятой, если число не целое
            if value.is_integer():
                return f"{int(value)}.0"
            return f"{value:.3f}".rstrip('0').rstrip('.') if '.' in f"{value:.3f}" else f"{value:.3f}"

        with open(filepath, 'w', encoding='utf-8') as f:
            # === Крыло ===
            # L = 31.100 // [m] dlina krila
            f.write("\n" + format_value(geometry.l_wing) + "\n")
            # Bo = 5.170 // [m] kornevaya horda krila
            f.write(format_value(geometry.b0_wing) + "\n")
            # Bk = 1.110 // [m] kontsevaya horda krila
            f.write(format_value(geometry.bk_wing) + "\n")
            # KsiLe = 28.100 // [deg] ugol strelovidnosti perednei kromki krila
            f.write(format_value(geometry.sweep_wing_LE) + "\n")
            # Yo = 0.0 // [m] Yo koordinata tochki kornya krila
            f.write(format_value(geometry.y_wing) + "\n\n")

            # === Горизонтальное оперение (ГО) ===
            # L = 3.100 // [m] dlina go
            f.write(format_value(geometry.l_ht) + "\n")
            # Bo = 0.570 // [m] kornevaya horda go
            f.write(format_value(geometry.b0_ht) + "\n")
            # Bk = 0.210 // [m] kontsevaya horda go
            f.write(format_value(geometry.bk_ht) + "\n")
            # KsiLe = 15.100 // [deg] ugol strelovidnosti perednei kromki go
            f.write(format_value(geometry.sweep_ht_LE) + "\n")
            # Xo = 15.0 // [m] Xo koordinata tochki kornya go
            f.write(format_value(geometry.x_ht) + "\n")
            # Yo = 0.0 // [m] Yo koordinata tochki kornya go
            f.write(format_value(geometry.y_ht) + "\n\n")

            # === Вертикальное оперение (ВО) ===
            # L = 2.100 // [m] dlina vo
            f.write(format_value(geometry.l_vt) + "\n")
            # Bo = 0.570 // [m] kornevaya horda vo
            f.write(format_value(geometry.b0_vt) + "\n")
            # Bk = 0.210 // [m] kontsevaya horda vo
            f.write(format_value(geometry.bk_vt) + "\n")
            # KsiLe = 38.100 // [deg] ugol strelovidnosti perednei kromki vo
            f.write(format_value(geometry.sweep_vt_LE) + "\n")
            # Xo = 15.0 // [m] Xo koordinata tochki kornya vo
            f.write(format_value(geometry.x_vt) + "\n\n")

            # === Фюзеляж ===
            # L = 28.0 // [m] dlina fuz
            f.write(format_value(geometry.L_fuselage) + "\n")
            # Bo = 1.450 // [m] max radius fuz
            f.write(format_value(geometry.r_fuselage) + "\n")  # Используем радиус
            # Xo = -7.0 // [m] Xo koordinata tochki 1 sechenia fuz
            f.write(format_value(geometry.x_fuselage) + "\n")

    @staticmethod
    def _find_field_by_russian_name(russian_name: str) -> Optional[str]:
        """
        Находит имя поля по русскому названию

        Args:
            russian_name: русское название параметра

        Returns:
            английское имя поля или None
        """
        # Ищем точное совпадение
        for eng_name, rus_name in FIELD_LABELS.items():
            if rus_name.lower() == russian_name.lower():
                return eng_name

        # Ищем частичное совпадение (первые слова)
        russian_words = russian_name.lower().split()
        for eng_name, rus_name in FIELD_LABELS.items():
            rus_words = rus_name.lower().split()
            if russian_words and rus_words and russian_words[0] == rus_words[0]:
                return eng_name

        return None

    @staticmethod
    def _set_field_value(data: ProjectData, field_name: str, value: str) -> None:
        """
        Устанавливает значение поля в ProjectData
        Поддерживает enum типы (EngineTypeEnum, WingFlapsTypeEnum)

        Args:
            data: объект ProjectData
            field_name: имя поля
            value: строковое значение для преобразования
        """
        try:
            # Пробуем установить значение в основных полях ProjectData
            if hasattr(data, field_name):
                attr = getattr(data, field_name)
                FileIO._set_attr_value(data, field_name, attr, value)
            else:
                # Пробуем найти в подструктурах (приоритет: landing → все остальные)
                found = False

                # Сначала пробуем landing_data (для engine_type и wing_flaps_type)
                if hasattr(data.landing_data, field_name):
                    attr = getattr(data.landing_data, field_name)
                    FileIO._set_attr_value(data.landing_data, field_name, attr, value)
                    found = True

                # Потом остальные подструктуры
                if not found:
                    for sub_data in [
                        data.preliminary_sizing, data.mass_estimation, data.geometry_data
                    ]:
                        if hasattr(sub_data, field_name):
                            attr = getattr(sub_data, field_name)
                            FileIO._set_attr_value(sub_data, field_name, attr, value)
                            found = True
                            break
        except Exception as e:
            print(f"⚠ Ошибка при установке {field_name} = {value}: {e}")

    @staticmethod
    def _set_attr_value(obj, field_name: str, attr, value: str) -> None:
        """Вспомогательный метод для установки значения атрибута"""

        # Обработка enum типов
        if attr is None or isinstance(attr, EngineTypeEnum):
            # Пробуем преобразовать в EngineTypeEnum
            try:
                if value.upper() in ['TURBOJET', 'TURBOPROP']:
                    enum_val = EngineTypeEnum[value.upper()]
                    setattr(obj, field_name, enum_val)
                    return
            except (KeyError, AttributeError):
                pass
        if attr is None or isinstance(attr, WingChemeEnum):
            # Пробуем преобразовать в EngineTypeEnum
            try:
                if value.upper() in ['LOW', 'MID', 'HIGH']:
                    setattr(obj, field_name, value)
                    return
            except (KeyError, AttributeError):
                pass

        if attr is None or isinstance(attr, WingFlapsTypeEnum):
            # Пробуем преобразовать в WingFlapsTypeEnum
            try:
                value_upper = value.upper()
                # Преобразуем различные варианты названий
                enum_mapping = {
                    'CLEAN_AIRFOIL': 'CLEAN_AIRFOIL',
                    'PLAIN_FLAP': 'PLAIN_FLAP',
                    'SPLIT_FLAP': 'SPLIT_FLAP',
                    'SLOTTED_FLAP': 'SLOTTED_FLAP',
                    'FOWLER_FLAP': 'FOWLER_FLAP',
                    'DOUBLE_SLOTTED_FLAP': 'DOUBLE_SLOTTED_FLAP',
                    'TRIPLE_SLOTTED_FLAP': 'TRIPLE_SLOTTED_FLAP',
                }

                if value_upper in enum_mapping:
                    enum_val = WingFlapsTypeEnum[enum_mapping[value_upper]]
                    setattr(obj, field_name, enum_val)
                    return
            except (KeyError, AttributeError):
                pass

        # Числовые типы с ВАЛИДАЦИЕЙ
        if isinstance(attr, (int, float)) or attr is None:
            try:
                # Специальная валидация для C_L_ma
                if field_name == 'C_L_ma':
                    num_val = float(value)
                    if num_val < 0 or num_val > 2.0:
                        print(f"⚠ {field_name} должен быть в диапазоне [0, 2.0], получено {num_val}")
                        return
                    setattr(obj, field_name, num_val)
                    return

                # Остальные числовые параметры
                if '.' in value:
                    setattr(obj, field_name, float(value))
                else:
                    setattr(obj, field_name, int(value))
            except ValueError:
                try:
                    setattr(obj, field_name, float(value))
                except ValueError:
                    print(f"⚠ Не удалось преобразовать {field_name} = {value}")

        # Строковые типы
        elif isinstance(attr, str):
            setattr(obj, field_name, value)

    @staticmethod
    def _get_field_value(data: ProjectData, field_name: str) -> Optional[any]:
        """
        Получает значение поля из ProjectData

        Args:
            data: объект ProjectData
            field_name: имя поля

        Returns:
            значение поля или None
        """
        # Проверяем основные поля
        if hasattr(data, field_name):
            value = getattr(data, field_name)
            if value is not None:
                return value

        # Проверяем подструктуры
        for sub_data in [
            data.preliminary_sizing, data.mass_estimation, data.geometry_data
        ]:
            if hasattr(sub_data, field_name):
                value = getattr(sub_data, field_name)
                if value is not None:
                    return value

        return None
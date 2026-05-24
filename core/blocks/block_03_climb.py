from typing import Dict, Any, List
import math
from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData
from core.exceptions import CalculationError


class Block03Climb(BaseBlock):
    """
    Блок 3: Определение параметров набора высоты
    Определяет количество двигателей, climb gradient и угол γ
    """

    @property
    def name(self) -> str:
        return "Параметры набора высоты"

    @property
    def block_number(self) -> int:
        return 3

    @property
    def required_inputs(self) -> List[str]:
        return [
            "climb_data.n_engines",       # Количество двигателей
            "climb_data.climb_gradient"   # Градиент набора высоты
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return []

    @property
    def outputs(self) -> List[str]:
        return ["climb_data.gamma_sin"]

    def calculate(self, data: ProjectData) -> None:
        """
        Выполняет расчёт угла набора высоты

        Формула 5.17 из методики: sin(γ) ≈ climb_gradient для малых углов
        """
        try:
            # Валидация входных данных
            validation_errors = self.validate(data)
            if validation_errors:
                raise CalculationError(
                    f"Ошибки валидации в блоке {self.name}: {validation_errors}",
                    self.name
                )

            # Получение входных данных
            n_engines = data.climb_data.n_engines
            climb_gradient = data.climb_data.climb_gradient

            if not n_engines or not climb_gradient:
                raise CalculationError(
                    "Отсутствуют обязательные данные: n_engines и climb_gradient",
                    self.name
                )

            # Проверка разумности данных
            if n_engines < 1 or n_engines > 8:
                raise CalculationError(
                    f"Недопустимое количество двигателей: {n_engines} (должно быть от 1 до 8)",
                    self.name
                )

            if climb_gradient <= 0 or climb_gradient > 0.5:
                raise CalculationError(
                    f"Недопустимый градиент набора: {climb_gradient} (должен быть от 0 до 0.5)",
                    self.name
                )

            # Основной расчёт: формула 5.17
            # Для малых углов sin(γ) ≈ γ ≈ climb_gradient
            # Для малых углов sin(γ) ≈ γ ≈ arctan(climb_gradient)
            gamma_sin = math.atan(climb_gradient)

            # Сохранение результатовййцййц
            data.climb_data.gamma_sin = gamma_sin

            print(f"Блок 3 - Результат: sin(γ) = {gamma_sin:.4f}, n_engines = {n_engines}")

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}",
                    self.name
                )

    def get_calculation_summary(self, data: ProjectData) -> Dict[str, Any]:
        """Сводка результатов расчёта"""
        base_summary = super().get_calculation_summary(data)

        if data.climb_data.gamma_sin is not None:
            base_summary['calculation_details'] = {
                'input_parameters': {
                    'n_engines': f"{data.climb_data.n_engines}" if data.climb_data.n_engines else "Не указано",
                    'climb_gradient': f"{data.climb_data.climb_gradient:.4f}" if data.climb_data.climb_gradient else "Не указан"
                },
                'final_result': {
                    'gamma_sin': f"{data.climb_data.gamma_sin:.4f}",
                    'gamma_degrees': f"{math.degrees(math.asin(data.climb_data.gamma_sin)):.2f}°",
                    'description': 'Угол набора высоты для 2-го сегмента'
                },
                'equations_used': [
                    'sin(γ) ≈ climb_gradient (для малых углов, формула 5.17)'
                ],
                'typical_gradients': {
                    'twin_engine': '2.4% (0.024)',
                    'three_engine': '2.7% (0.027)', 
                    'four_engine': '3.0% (0.030)'
                }
            }

        return base_summary
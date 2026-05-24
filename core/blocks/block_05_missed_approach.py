from typing import Dict, Any, List
import math
from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData
from core.exceptions import CalculationError


class Block05MissedApproach(BaseBlock):
    """
    Блок 5: Параметры прерванной посадки (Missed Approach)
    Определяет градиент набора для прерванной посадки и угол γ_MA
    """

    @property
    def name(self) -> str:
        return "Прерванная посадка"

    @property
    def block_number(self) -> int:
        return 5

    @property
    def required_inputs(self) -> List[str]:
        return [
            "missed_approach_data.climb_gradient_ma"   # Градиент набора для missed approach
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return [
            "climb_data.n_engines"  # Используем количество двигателей из блока 3, если доступно
        ]

    @property
    def outputs(self) -> List[str]:
        return ["missed_approach_data.gamma_sin_ma"]

    def calculate(self, data: ProjectData) -> None:
        """
        Выполняет расчёт угла набора высоты для прерванной посадки

        Формула 5.17 из методики: sin(γ_MA) ≈ climb_gradient_ma для малых углов
        Используется для расчёта T/W в блоке 6
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
            climb_gradient_ma = data.missed_approach_data.climb_gradient_ma

            if climb_gradient_ma is None:
                raise CalculationError(
                    "Отсутствуют обязательные данные: climb_gradient_ma",
                    self.name
                )

            # Проверка разумности данных
            if climb_gradient_ma <= 0 or climb_gradient_ma > 0.5:
                raise CalculationError(
                    f"Недопустимый градиент набора: {climb_gradient_ma} (должен быть от 0 до 0.5)",
                    self.name
                )

            # Основной расчёт: формула 5.17 для прерванной посадки
            # Для малых углов sin(γ_MA) ≈ γ_MA ≈ climb_gradient_ma
            gamma_sin_ma = climb_gradient_ma

            # Сохранение результатов
            data.missed_approach_data.gamma_sin_ma = gamma_sin_ma

            # Получаем количество двигателей из блока 3, если доступно
            n_engines = data.climb_data.n_engines if data.climb_data.n_engines else None

            print(f"Блок 5 - Результат: sin(γ_MA) = {gamma_sin_ma:.4f}")
            if n_engines:
                print(f"Блок 5 - Используется {n_engines} двигателей из блока 3")

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

        if data.missed_approach_data.gamma_sin_ma is not None:
            base_summary['calculation_details'] = {
                'input_parameters': {
                    'climb_gradient_ma': f"{data.missed_approach_data.climb_gradient_ma:.4f}" if data.missed_approach_data.climb_gradient_ma else "Не указан",
                    'n_engines_from_block3': f"{data.climb_data.n_engines}" if data.climb_data.n_engines else "Не определено"
                },
                'final_result': {
                    'gamma_sin_ma': f"{data.missed_approach_data.gamma_sin_ma:.4f}",
                    'gamma_degrees': f"{math.degrees(math.asin(data.missed_approach_data.gamma_sin_ma)):.2f}°",
                    'description': 'Угол набора высоты для прерванной посадки'
                },
                'equations_used': [
                    'sin(γ_MA) ≈ climb_gradient_ma (для малых углов, формула 5.17)'
                ],
                'typical_gradients_missed_approach': {
                    'twin_engine': '2.1% (0.021)',
                    'three_engine': '2.4% (0.024)',
                    'four_engine': '2.7% (0.027)'
                },
                'configuration_notes': [
                    'Прерванная посадка выполняется в посадочной конфигурации',
                    'Шасси выпущено, закрылки в посадочном положении',
                    'Один двигатель отказал, остальные на взлётной тяге'
                ]
            }

        return base_summary
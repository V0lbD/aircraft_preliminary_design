"""
Оркестратор расчётов - запускает все блоки 1-8 последовательно
"""

import sys
from pathlib import Path
from typing import Optional, List

# Добавляем путь к основному проекту
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.data_models import ProjectData
from core.exceptions import CalculationError

from core.block_preliminary_sizing import BlockPreliminarySizing
from core.block_mass_estimation import BlockMassEstimation
from core.block_geometry import BlockGeometry

class CalculationEngine:
    """
    Оркестратор расчётов
    Запускает блоки 1-8 последовательно и заполняет ProjectData результатами
    """
    
    def __init__(self):
        """Инициализирует движок расчётов"""
        self.blocks = [
            ("Блок 1: Предварительное определение параметров", BlockPreliminarySizing()),
            ("Блок 2: Оценка масс", BlockMassEstimation()),
            ("Блок 3: Геометрия", BlockGeometry()),
        ]
        
        self.calculation_log: List[str] = []
        self.errors: List[str] = []
    
    def calculate(self, data: ProjectData) -> bool:
        """
        Выполняет последовательно все расчёты
        
        Args:
            data: ProjectData с входными данными
            
        Returns:
            True если расчёты успешны, False если есть ошибки
        """
        self.calculation_log.clear()
        self.errors.clear()
        
        for block_name, block in self.blocks:
            try:
                self.calculation_log.append(f"➤ Выполняю {block_name}...")
                
                # Валидация входных данных для блока
                validation_errors = block.validate(data)
                if validation_errors:
                    error_msg = f"{block_name}: {', '.join(validation_errors)}"
                    self.errors.append(error_msg)
                    self.calculation_log.append(f"✗ {error_msg}")
                    # Продолжаем, может быть блок не критичный
                    continue
                
                # Выполняем расчёт
                block.calculate(data)
                self.calculation_log.append(f"✓ {block_name} завершён успешно")
                
            except CalculationError as e:
                error_msg = f"{block_name}: {str(e)}"
                self.errors.append(error_msg)
                self.calculation_log.append(f"✗ ОШИБКА: {error_msg}")
                
                # Для блоков 1, 2, 4, 7 ошибка критична (нужны они для блока 8)
                if block_name in ["Блок 1: Посадка", "Блок 2: Взлёт", 
                                 "Блок 4: Крейсер и тяговооружённость",
                                 "Блок 7: T/W прерванной посадки"]:
                    self.calculation_log.append(f"⚠ Прерывание расчётов: критичный блок")
                    return False
            
            except Exception as e:
                error_msg = f"{block_name}: Неожиданная ошибка: {str(e)}"
                self.errors.append(error_msg)
                self.calculation_log.append(f"✗ {error_msg}")
                return False
        
        self.calculation_log.append("=" * 60)
        self.calculation_log.append("✓ ВСЕ РАСЧЁТЫ УСПЕШНО ЗАВЕРШЕНЫ")
        self.calculation_log.append("=" * 60)

        return len(self.errors) == 0
    
    def get_log(self) -> str:
        """Возвращает лог расчётов как одну строку"""
        return "\n".join(self.calculation_log)
    
    def get_errors(self) -> List[str]:
        """Возвращает список ошибок"""
        return self.errors.copy()
    
    def has_errors(self) -> bool:
        """Проверяет, были ли ошибки"""
        return len(self.errors) > 0

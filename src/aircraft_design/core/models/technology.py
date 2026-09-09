from __future__ import annotations

from pydantic import BaseModel, Field

class TechCoefficients(BaseModel):
    """Коэффициенты для конкретной технологии и агрегата."""
    skin: float = Field(0.0, description="Обшивка")
    longitudinal: float = Field(0.0, description="Продольный набор")
    transverse: float = Field(0.0, description="Поперечный набор")

class ComponentTechnologies(BaseModel):
    """Доступные технологии для одного агрегата (крыло/фюзеляж/оперение)."""
    alum_1: TechCoefficients = Field(default_factory=TechCoefficients, description="Алюминий (строка 3)")
    alum_2: TechCoefficients = Field(default_factory=TechCoefficients, description="Алюминий (строка 4)")
    comp_1: TechCoefficients = Field(default_factory=TechCoefficients, description="Композит (строка 5)")
    comp_2: TechCoefficients = Field(default_factory=TechCoefficients, description="Композит (строка 6)")

class TableData(BaseModel):
    """Данные одной стандартной таблицы (Таблицы 1-9)."""
    wing: ComponentTechnologies = Field(default_factory=ComponentTechnologies)
    fuselage: ComponentTechnologies = Field(default_factory=ComponentTechnologies)
    tail: ComponentTechnologies = Field(default_factory=ComponentTechnologies)

class GlobalCoefficients(BaseModel):
    """Глобальные коэффициенты из Таблицы 10."""
    k_skl: float = Field(1.0, description="KSKL - К-т площади склада")
    k_oper: float = Field(1.0, description="KOPER - К-т межоперационных площадей")
    k_prod: float = Field(1.0, description="KPROD - К-т готовой продукции")
    k_ras: float = Field(1.0, description="KRAS - К-т расходных материалов")
    k_vspom: float = Field(1.0, description="KVSPOM - К-т расходных материалов (вспом.)")
    k_sb: float = Field(1.0, description="KSB - К-т для 1 рабочего (бытовые)")
    k_adm: float = Field(1.0, description="KADM - К-т доли адм. работников")
    s_k_adm: float = Field(1.0, description="SKADM - К-т площади на адм. раб.")
    c_1m: float = Field(1.0, description="S1M - Стоимость 1 кв. метра")
    k_prib: float = Field(1.0, description="KPRIB - К-т прибыли")

class TechnologyDatabase(BaseModel):
    """Полная база данных технологий (собрана из всех таблиц)."""
    nel: TableData      # Таблица 1. Кол-во элементов
    ndet: TableData     # Таблица 2. Кол-во деталей на станке
    m_el: TableData     # Таблица 3. Относительные массы
    kim: TableData      # Таблица 4. КИМ
    c1: TableData       # Таблица 5. Стоимость 1 кг
    cst1: TableData     # Таблица 6. Стоимость станка
    nrb: TableData      # Таблица 7. Кол-во сотрудников
    cnrb: TableData     # Таблица 8. Зарплата
    s1: TableData       # Таблица 9. Площадь 1 станка
    globals: GlobalCoefficients # Таблица 10
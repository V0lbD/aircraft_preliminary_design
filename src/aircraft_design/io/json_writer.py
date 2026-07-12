from pathlib import Path
from aircraft_design.core.models.project import ProjectInput, ProjectResult


def write_project_input(project_input: ProjectInput, file_path: str | Path) -> None:
    """
    Сохраняет входные данные проекта в JSON.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Pydantic сам генерирует красивый JSON
    json_data = project_input.model_dump_json(indent=4)
    path.write_text(json_data, encoding="utf-8")


def write_project_result(project_result: ProjectResult, file_path: str | Path) -> None:
    """
    Сохраняет результаты расчетов в JSON.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    json_data = project_result.model_dump_json(indent=4)
    path.write_text(json_data, encoding="utf-8")
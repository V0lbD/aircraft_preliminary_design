from pathlib import Path
from aircraft_design.core.models.project import ProjectInput
from aircraft_design.core.errors import InputValidationError
from pydantic import ValidationError

def load_project_input(file_path: str | Path) -> ProjectInput:
    """
    Загружает входные данные проекта из JSON файла.
    """
    path = Path(file_path)
    if not path.is_file():
        raise InputValidationError(f"Файл не найден: {path}")

    try:
        json_content = path.read_text(encoding="utf-8")
        # Pydantic сам распарсит строку и проверит все типы
        return ProjectInput.model_validate_json(json_content)
    except ValidationError as e:
        raise InputValidationError(f"Ошибка валидации структуры файла {path.name}:\n{e}")
    except Exception as e:
        raise InputValidationError(f"Ошибка при чтении файла {path.name}: {e}")
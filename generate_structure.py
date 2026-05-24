import os

def list_files(startpath, exclude_dirs={'.venv', '__pycache__', '.git', 'dist', 'build', '.idea', '.vscode'}):
    with open('project_structure.txt', 'w', encoding='utf-8') as f:
        for root, dirs, files in os.walk(startpath):
            # Убираем исключенные папки прямо из списка для обхода
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            level = root.replace(startpath, '').count(os.sep)
            indent = '│   ' * level
            f.write(f'{indent}├── {os.path.basename(root)}/\n')
            sub_indent = '│   ' * (level + 1)
            for file in files:
                f.write(f'{sub_indent}├── {file}\n')

if __name__ == "__main__":
    print("Генерация структуры проекта...")
    # Замените '.' на путь к вашему проекту, если скрипт запускается не из корня
    list_files('.')
    print("Готово! Структура сохранена в файл 'project_structure.txt'")
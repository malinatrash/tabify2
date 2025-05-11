import re

def validate_tablature_text(new_text, original_text=None):
    """
    Валидирует текстовое представление табулатуры с использованием регулярных выражений
    :param new_text: Новый текст табулатуры
    :param original_text: Оригинальный текст табулатуры для сравнения (опционально)
    :return: Словарь с результатами валидации {"valid": True/False, "error": ""}
    """
    # Проверяем базовые условия
    if not new_text:
        return {"valid": False, "error": "Текст табулатуры не может быть пустым"}

    # Проверяем, что пользователь не удалил строки, если есть оригинальный текст
    if original_text:
        original_lines = original_text.strip().split('\n')
        new_lines = new_text.strip().split('\n')
        if len(new_lines) < len(original_lines):
            return {
                "valid": False, 
                "error": f"Удаление строк не разрешено. Удалено {len(original_lines) - len(new_lines)} строк"
            }

    # Регулярные выражения для строк табулатуры
    string_line_regex = {
        'e': re.compile(r'^[eE]\|[-0-9hpb\/\\xrs]*\|$'),
        'B': re.compile(r'^[bB]\|[-0-9hpb\/\\xrs]*\|$'),
        'G': re.compile(r'^[gG]\|[-0-9hpb\/\\xrs]*\|$'),
        'D': re.compile(r'^[dD]\|[-0-9hpb\/\\xrs]*\|$'),
        'A': re.compile(r'^[aA]\|[-0-9hpb\/\\xrs]*\|$'),
        'E': re.compile(r'^[eE]\|[-0-9hpb\/\\xrs]*\|$'),
    }

    # Паттерн для проверки недопустимых символов
    invalid_chars_pattern = re.compile(r'[^a-zA-Z0-9|\-\/\\phbxrs\s\n\t]')

    # Проверяем каждую строку на соответствие формату
    lines = new_text.strip().split('\n')
    for i, line in enumerate(lines):
        # Пропускаем пустые строки или комментарии
        if not line.strip() or line.strip().startswith('//') or line.strip().startswith('#'):
            continue

        # Проверка строк с обозначением струн
        for string_name, pattern in string_line_regex.items():
            if line.strip().startswith(f'{string_name}|') or line.strip().startswith(f'{string_name.lower()}|'):
                if not pattern.match(line.strip()):
                    return {
                        "valid": False,
                        "error": f"Неверный формат струны {string_name} в строке {i+1}: '{line.strip()}'"
                    }

        # Проверка на недопустимые символы
        if invalid_chars_pattern.search(line):
            return {
                "valid": False,
                "error": f"Недопустимые символы в строке {i+1}: '{line.strip()}'"
            }

    # Если все проверки пройдены, табулатура валидна
    return {"valid": True, "error": ""}

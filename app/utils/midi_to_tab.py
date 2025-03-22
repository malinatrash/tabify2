"""
Модуль для конвертации MIDI-файлов в табулатуры.
Использует библиотеки music21 и mido для анализа файлов MIDI и создания табулатур.
"""
from typing import Dict, List, Tuple, Optional
import pretty_midi
from music21 import converter, note, chord, stream, pitch

# Словарь соответствия MIDI-нот струнам гитары и позициям ладов
# Формат: {midi_note: (string_number, fret_position)}
# Струны нумеруются сверху вниз от 1 до 6 (от высокой E до низкой E)
GUITAR_MAPPING = {
    # Струна 1 (высокая E / E4)
    64: (1, 0),  # E4 (открытая 1-я струна)
    65: (1, 1),  # F4
    66: (1, 2),  # F#4
    67: (1, 3),  # G4
    68: (1, 4),  # G#4
    69: (1, 5),  # A4
    70: (1, 6),  # A#4
    71: (1, 7),  # B4
    72: (1, 8),  # C5
    73: (1, 9),  # C#5
    74: (1, 10), # D5
    75: (1, 11), # D#5
    76: (1, 12), # E5
    
    # Струна 2 (B / B3)
    59: (2, 0),  # B3 (открытая 2-я струна)
    60: (2, 1),  # C4
    61: (2, 2),  # C#4
    62: (2, 3),  # D4
    63: (2, 4),  # D#4
    64: (2, 5),  # E4 (также может быть сыграна на 1-й струне)
    65: (2, 6),  # F4
    66: (2, 7),  # F#4
    67: (2, 8),  # G4
    68: (2, 9),  # G#4
    69: (2, 10), # A4
    70: (2, 11), # A#4
    71: (2, 12), # B4
    
    # Струна 3 (G / G3)
    55: (3, 0),  # G3 (открытая 3-я струна)
    56: (3, 1),  # G#3
    57: (3, 2),  # A3
    58: (3, 3),  # A#3
    59: (3, 4),  # B3
    60: (3, 5),  # C4
    61: (3, 6),  # C#4
    62: (3, 7),  # D4
    63: (3, 8),  # D#4
    64: (3, 9),  # E4
    65: (3, 10), # F4
    66: (3, 11), # F#4
    67: (3, 12), # G4
    
    # Струна 4 (D / D3)
    50: (4, 0),  # D3 (открытая 4-я струна)
    51: (4, 1),  # D#3
    52: (4, 2),  # E3
    53: (4, 3),  # F3
    54: (4, 4),  # F#3
    55: (4, 5),  # G3
    56: (4, 6),  # G#3
    57: (4, 7),  # A3
    58: (4, 8),  # A#3
    59: (4, 9),  # B3
    60: (4, 10), # C4
    61: (4, 11), # C#4
    62: (4, 12), # D4
    
    # Струна 5 (A / A2)
    45: (5, 0),  # A2 (открытая 5-я струна)
    46: (5, 1),  # A#2
    47: (5, 2),  # B2
    48: (5, 3),  # C3
    49: (5, 4),  # C#3
    50: (5, 5),  # D3
    51: (5, 6),  # D#3
    52: (5, 7),  # E3
    53: (5, 8),  # F3
    54: (5, 9),  # F#3
    55: (5, 10), # G3
    56: (5, 11), # G#3
    57: (5, 12), # A3
    
    # Струна 6 (низкая E / E2)
    40: (6, 0),  # E2 (открытая 6-я струна)
    41: (6, 1),  # F2
    42: (6, 2),  # F#2
    43: (6, 3),  # G2
    44: (6, 4),  # G#2
    45: (6, 5),  # A2
    46: (6, 6),  # A#2
    47: (6, 7),  # B2
    48: (6, 8),  # C3
    49: (6, 9),  # C#3
    50: (6, 10), # D3
    51: (6, 11), # D#3
    52: (6, 12), # E3
}

class TabNote:
    """Класс для представления ноты в табулатуре."""
    
    def __init__(self, string: int, fret: int, duration: float, start_time: float):
        """
        Инициализация ноты табулатуры.
        
        Args:
            string: Номер струны (1-6, от высокой E до низкой E)
            fret: Позиция лада
            duration: Длительность ноты в долях такта
            start_time: Время начала ноты в долях такта
        """
        self.string = string
        self.fret = fret
        self.duration = duration
        self.start_time = start_time
    
    def __repr__(self) -> str:
        return f"TabNote(string={self.string}, fret={self.fret}, duration={self.duration}, start_time={self.start_time})"

class Tablature:
    """Класс для представления гитарной табулатуры."""
    
    def __init__(self):
        """Инициализация пустой табулатуры."""
        # Будем хранить ноты по временным отрезкам (тактам)
        self.measures = []
        self.current_measure = []
        self.measure_duration = 4.0  # По умолчанию 4/4
        self.current_time = 0.0
    
    def add_note(self, tab_note: TabNote):
        """Добавить ноту в табулатуру."""
        # Если нота выходит за пределы текущего такта, создаем новый такт
        if tab_note.start_time >= self.current_time + self.measure_duration:
            self.measures.append(self.current_measure)
            self.current_measure = []
            self.current_time += self.measure_duration
        
        self.current_measure.append(tab_note)
    
    def finalize(self):
        """Завершить создание табулатуры, добавив последний такт."""
        if self.current_measure:
            self.measures.append(self.current_measure)
    
    def to_text_format(self) -> str:
        """Преобразовать табулатуру в текстовый формат."""
        self.finalize()
        
        # Если нет нот, возвращаем пустую табулатуру
        if not self.measures:
            return "Пустая табулатура"
        
        result = []
        
        # Заголовок табулатуры
        result.append("Табулатура")
        result.append("=" * 40)
        
        # Для каждого такта создаем текстовое представление
        for measure_idx, measure in enumerate(self.measures):
            # Создаем 6 строк для струн
            strings = ["E|", "B|", "G|", "D|", "A|", "E|"]
            
            # Если в такте нет нот, добавляем пустой такт
            if not measure:
                for i in range(6):
                    strings[i] += "----|"
            else:
                # Вычисляем максимальную длину такта в символах
                max_len = 30  # Произвольное минимальное значение для читаемости
                
                # Сортируем ноты по времени начала
                measure.sort(key=lambda x: x.start_time)
                
                # Добавляем ноты на соответствующие струны
                for note in measure:
                    # Находим позицию в строке для этой ноты
                    pos = int(20 * (note.start_time - self.current_time) / self.measure_duration)
                    
                    # Добавляем дефисы до позиции ноты
                    while len(strings[note.string - 1]) < pos + 2:  # +2 для учета начальных символов "X|"
                        strings[note.string - 1] += "-"
                    
                    # Добавляем номер лада
                    fret_str = str(note.fret)
                    strings[note.string - 1] += fret_str
                    
                    # Обновляем максимальную длину, если нужно
                    max_len = max(max_len, len(strings[note.string - 1]) + 5)  # +5 для добавления хвоста
                
                # Добавляем хвосты строк и разделитель такта
                for i in range(6):
                    while len(strings[i]) < max_len:
                        strings[i] += "-"
                    strings[i] += "|"
            
            # Добавляем строки в результат
            result.extend(strings)
            # Пустая строка между тактами
            result.append("")
        
        return "\n".join(result)
    
    def to_json(self) -> dict:
        """Преобразовать табулатуру в формат JSON для AlphaTab."""
        self.finalize()
        
        # Создаем структуру AlphaTab
        alphatab_data = {
            "tracks": [
                {
                    "name": "Guitar",
                    "tuning": [40, 45, 50, 55, 59, 64],  # E2, A2, D3, G3, B3, E4
                    "measures": []
                }
            ]
        }
        
        # Для каждого такта создаем JSON представление
        for measure_idx, measure in enumerate(self.measures):
            # Создаем такт
            measure_data = {
                "index": measure_idx,
                "voices": [
                    {
                        "beats": []
                    }
                ]
            }
            
            # Если в такте есть ноты, добавляем их
            if measure:
                # Сортируем ноты по времени начала
                measure.sort(key=lambda x: x.start_time)
                
                # Группируем ноты по временным отрезкам
                time_groups = {}
                for note in measure:
                    # Округляем время до ближайшей 1/16 ноты
                    time_key = round(note.start_time * 16) / 16
                    if time_key not in time_groups:
                        time_groups[time_key] = []
                    time_groups[time_key].append(note)
                
                # Сортируем временные отрезки
                sorted_times = sorted(time_groups.keys())
                
                # Для каждого временного отрезка создаем бит
                for time_key in sorted_times:
                    notes_at_time = time_groups[time_key]
                    
                    # Создаем бит
                    beat = {
                        "notes": []
                    }
                    
                    # Добавляем все ноты в бит
                    for note in notes_at_time:
                        beat["notes"].append({
                            "string": note.string,
                            "fret": note.fret,
                            "duration": "w"  # Целая нота по умолчанию
                        })
                    
                    measure_data["voices"][0]["beats"].append(beat)
            
            # Добавляем такт в трек
            alphatab_data["tracks"][0]["measures"].append(measure_data)
        
        return alphatab_data


def find_best_position(midi_note: int) -> Tuple[int, int]:
    """Находит наилучшую позицию на грифе для MIDI-ноты.
    
    Args:
        midi_note: MIDI-нота (0-127)
    
    Returns:
        Tuple[int, int]: (строка, лад)
    """
    # Если нота есть в словаре, возвращаем её позицию
    if midi_note in GUITAR_MAPPING:
        return GUITAR_MAPPING[midi_note]
    
    # Если нота слишком низкая или высокая, приближаем её к доступному диапазону
    if midi_note < 40:  # Ниже низкой E (E2)
        return (6, 0)  # Открытая 6-я струна (низкая E)
    elif midi_note > 76:  # Выше высокой E на 12-м ладу (E5)
        return (1, 12)  # 12-й лад 1-й струны
    
    # В противном случае находим ближайшую ноту (что не должно происходить при хорошем маппинге)
    closest_note = min(GUITAR_MAPPING.keys(), key=lambda x: abs(x - midi_note))
    return GUITAR_MAPPING[closest_note]


def convert_midi_to_tablature(midi_file_path: str) -> dict:
    """Конвертирует MIDI-файл в табулатуру.
    
    Args:
        midi_file_path: Путь к MIDI-файлу
    
    Returns:
        dict: Табулатура в формате JSON для AlphaTab
    """
    try:
        # Загружаем MIDI-файл
        midi_data = pretty_midi.PrettyMIDI(midi_file_path)
        
        # Создаем пустую табулатуру
        tab = Tablature()
        
        # Перебираем все инструменты и ноты
        for instrument in midi_data.instruments:
            # Пропускаем ударные
            if instrument.is_drum:
                continue
            
            # Добавляем каждую ноту в табулатуру
            for note in instrument.notes:
                # Получаем MIDI-номер ноты
                midi_note = note.pitch
                
                # Находим позицию на грифе
                string, fret = find_best_position(midi_note)
                
                # Преобразуем время в доли такта
                start_time = note.start
                duration = note.end - note.start
                
                # Создаем ноту табулатуры
                tab_note = TabNote(string, fret, duration, start_time)
                
                # Добавляем ноту в табулатуру
                tab.add_note(tab_note)
        
        # Финализируем табулатуру
        tab.finalize()
        
        # Возвращаем JSON представление
        return tab.to_json()
    
    except Exception as e:
        print(f"Ошибка при конвертации MIDI в табулатуру: {e}")
        # Возвращаем пустую табулатуру в случае ошибки
        return {"tracks": [{"name": "Guitar", "tuning": [40, 45, 50, 55, 59, 64], "measures": []}]}


def midi_to_tablature(midi_data) -> Tablature:
    """Конвертирует данные MIDI в объект табулатуры.
    
    Args:
        midi_data: Данные MIDI (может быть путь к файлу или объект MIDI)
    
    Returns:
        Tablature: Объект табулатуры
    """
    # Создаем пустую табулатуру
    tab = Tablature()
    
    try:
        # Если midi_data - это путь к файлу
        if isinstance(midi_data, str):
            midi = pretty_midi.PrettyMIDI(midi_data)
        else:
            # Если midi_data - это объект MIDI
            midi = midi_data
        
        # Перебираем все инструменты и ноты
        for instrument in midi.instruments:
            # Пропускаем ударные
            if instrument.is_drum:
                continue
            
            # Добавляем каждую ноту в табулатуру
            for note in instrument.notes:
                # Получаем MIDI-номер ноты
                midi_note = note.pitch
                
                # Находим позицию на грифе
                string, fret = find_best_position(midi_note)
                
                # Преобразуем время в доли такта
                start_time = note.start
                duration = note.end - note.start
                
                # Создаем ноту табулатуры
                tab_note = TabNote(string, fret, duration, start_time)
                
                # Добавляем ноту в табулатуру
                tab.add_note(tab_note)
    
    except Exception as e:
        print(f"Ошибка при создании табулатуры: {e}")
    
    return tab


def save_tablature(tab_data) -> str:
    """Сохраняет данные табулатуры в текстовом формате.
    
    Args:
        tab_data: Данные табулатуры в формате JSON или объект Tablature
    
    Returns:
        str: Текстовое представление табулатуры
    """
    if isinstance(tab_data, Tablature):
        # Если tab_data - это объект Tablature
        return tab_data.to_text_format()
    
    # Если tab_data - это словарь (JSON)
    try:
        # Преобразуем JSON в объект табулатуры
        tab = Tablature()
        
        # Извлекаем ноты из JSON
        if "tracks" in tab_data and len(tab_data["tracks"]) > 0:
            track = tab_data["tracks"][0]
            
            # Перебираем все такты
            for measure in track.get("measures", []):
                for voice in measure.get("voices", []):
                    for beat in voice.get("beats", []):
                        for note in beat.get("notes", []):
                            # Создаем ноту табулатуры
                            string = note.get("string", 1)
                            fret = note.get("fret", 0)
                            duration = 1.0  # По умолчанию четвертная нота
                            start_time = 0.0  # Временно
                            
                            tab_note = TabNote(string, fret, duration, start_time)
                            tab.add_note(tab_note)
        
        # Возвращаем текстовое представление
        return tab.to_text_format()
    
    except Exception as e:
        print(f"Ошибка при сохранении табулатуры: {e}")
        return "Ошибка при сохранении табулатуры"
    
    def to_json(self) -> dict:
        """Преобразовать табулатуру в JSON-совместимый формат."""
        self.finalize()
        
        measures_json = []
        for measure in self.measures:
            measure_json = []
            for note in measure:
                measure_json.append({
                    "string": note.string,
                    "fret": note.fret,
                    "duration": note.duration,
                    "start_time": note.start_time
                })
            measures_json.append(measure_json)
        
        return {
            "measures": measures_json,
            "measure_duration": self.measure_duration
        }

def find_best_position(midi_note: int) -> Optional[Tuple[int, int]]:
    """
    Найти оптимальную позицию (струна, лад) для заданной MIDI-ноты.
    
    Args:
        midi_note: MIDI-номер ноты
    
    Returns:
        Кортеж (струна, лад) или None, если нота не может быть сыграна на гитаре
    """
    if midi_note in GUITAR_MAPPING:
        return GUITAR_MAPPING[midi_note]
    
    # Если ноты нет в маппинге, она может быть слишком низкой или слишком высокой для гитары
    return None

def midi_to_tablature(midi_file_path: str) -> Tablature:
    """
    Конвертировать MIDI-файл в табулатуру.
    
    Args:
        midi_file_path: Путь к MIDI-файлу
    
    Returns:
        Объект Tablature с табулатурой
    """
    # Загружаем MIDI-файл с помощью pretty_midi
    try:
        midi_data = pretty_midi.PrettyMIDI(midi_file_path)
    except Exception as e:
        print(f"Ошибка при загрузке MIDI-файла: {e}")
        return Tablature()  # Возвращаем пустую табулатуру в случае ошибки
    
    # Создаем новую табулатуру
    tablature = Tablature()
    
    # Обрабатываем каждый инструмент в MIDI-файле
    for instrument in midi_data.instruments:
        # Пропускаем ударные
        if instrument.is_drum:
            continue
        
        # Обрабатываем каждую ноту в инструменте
        for note in instrument.notes:
            # Находим наилучшую позицию для этой ноты на гитаре
            position = find_best_position(note.pitch)
            if position:
                string, fret = position
                # Получаем время начала и длительность ноты в долях такта
                start_time = note.start
                duration = note.end - note.start
                
                # Создаем объект TabNote и добавляем его в табулатуру
                tab_note = TabNote(string, fret, duration, start_time)
                tablature.add_note(tab_note)
    
    # Финализируем табулатуру
    tablature.finalize()
    
    return tablature

# Функция для сохранения табулатуры в файл
def save_tablature(tablature: Tablature, output_path: str, format_type: str = 'text'):
    """
    Сохранить табулатуру в файл.
    
    Args:
        tablature: Объект Tablature
        output_path: Путь для сохранения файла
        format_type: Формат сохранения ('text' или 'json')
    """
    if format_type == 'text':
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tablature.to_text_format())
    elif format_type == 'json':
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(tablature.to_json(), f, ensure_ascii=False, indent=2)
    else:
        raise ValueError(f"Неподдерживаемый формат: {format_type}")

# Пример использования
if __name__ == "__main__":
    # Путь к MIDI-файлу
    midi_file = "path/to/your/midi/file.mid"
    
    # Конвертируем MIDI в табулатуру
    tab = midi_to_tablature(midi_file)
    
    # Сохраняем табулатуру в текстовый файл
    save_tablature(tab, "output_tab.txt", "text")
    
    # Сохраняем табулатуру в JSON
    save_tablature(tab, "output_tab.json", "json")
    
    # Выводим табулатуру на экран
    print(tab.to_text_format())

from typing import Dict, List, Tuple, Optional
import mido
from music21 import converter, note, chord, stream, pitch

GUITAR_MAPPING = {

    64: (1, 0),
    65: (1, 1),
    66: (1, 2),
    67: (1, 3),
    68: (1, 4),
    69: (1, 5),
    70: (1, 6),
    71: (1, 7),
    72: (1, 8),
    73: (1, 9),
    74: (1, 10),
    75: (1, 11),
    76: (1, 12),

    59: (2, 0),
    60: (2, 1),
    61: (2, 2),
    62: (2, 3),
    63: (2, 4),
    64: (2, 5),
    65: (2, 6),
    66: (2, 7),
    67: (2, 8),
    68: (2, 9),
    69: (2, 10),
    70: (2, 11),
    71: (2, 12),

    55: (3, 0),
    56: (3, 1),
    57: (3, 2),
    58: (3, 3),
    59: (3, 4),
    60: (3, 5),
    61: (3, 6),
    62: (3, 7),
    63: (3, 8),
    64: (3, 9),
    65: (3, 10),
    66: (3, 11),
    67: (3, 12),

    50: (4, 0),
    51: (4, 1),
    52: (4, 2),
    53: (4, 3),
    54: (4, 4),
    55: (4, 5),
    56: (4, 6),
    57: (4, 7),
    58: (4, 8),
    59: (4, 9),
    60: (4, 10),
    61: (4, 11),
    62: (4, 12),

    45: (5, 0),
    46: (5, 1),
    47: (5, 2),
    48: (5, 3),
    49: (5, 4),
    50: (5, 5),
    51: (5, 6),
    52: (5, 7),
    53: (5, 8),
    54: (5, 9),
    55: (5, 10),
    56: (5, 11),
    57: (5, 12),

    40: (6, 0),
    41: (6, 1),
    42: (6, 2),
    43: (6, 3),
    44: (6, 4),
    45: (6, 5),
    46: (6, 6),
    47: (6, 7),
    48: (6, 8),
    49: (6, 9),
    50: (6, 10),
    51: (6, 11),
    52: (6, 12),
}


class TabNote:
    """Класс для представления ноты в табулатуре."""

    def __init__(self, string: int, fret: int, duration: float, start_time: float, tempo=120):
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
        self.tempo = tempo

    def __repr__(self) -> str:
        return f"TabNote(string={self.string}, fret={self.fret}, duration={self.duration}, start_time={self.start_time})"


class Tablature:
    """Класс для представления гитарной табулатуры."""

    def __init__(self):
        """Инициализация пустой табулатуры."""
        self.measures = []
        self.current_measure = []
        self.measure_duration = 4.0
        self.current_time = 0.0

    def add_note(self, tab_note: TabNote):
        """Добавить ноту в табулатуру."""
        if tab_note.start_time >= self.current_time + self.measure_duration:
            if self.current_measure:
                self.measures.append(self.current_measure)
                self.current_measure = []
            self.current_time += self.measure_duration

        self.current_measure.append(tab_note)

    def finalize(self):
        """Завершить создание табулатуры."""
        if self.current_measure:
            self.measures.append(self.current_measure)
            self.current_measure = []

    def to_text(self):
        """
        Преобразует табулатуру в текстовое представление с точным расположением нот по времени
        """
        all_notes = []
        for measure in self.measures:
            all_notes.extend(measure)

        if not all_notes:
            return ""

        # Сортируем ноты по времени начала
        all_notes.sort(key=lambda x: x.start_time)

        # Получаем временные границы
        start_time = all_notes[0].start_time
        end_time = all_notes[-1].start_time
        duration = end_time - start_time
        
        # Получаем темп
        tempo = all_notes[0].tempo if hasattr(all_notes[0], 'tempo') else 120
        
        # Анализируем временные интервалы между нотами
        time_gaps = []
        for i in range(1, len(all_notes)):
            time_gap = all_notes[i].start_time - all_notes[i-1].start_time
            time_gaps.append(time_gap)
        
        # Если есть временные интервалы, находим минимальный и средний
        min_gap = min(time_gaps) if time_gaps else duration
        avg_gap = sum(time_gaps) / len(time_gaps) if time_gaps else duration
        
        # Вычисляем количество символов для минимального интервала
        # Минимальный интервал между нотами должен быть не менее 3 символов
        # Это позволит разместить двухзначные числа (например, 10, 11) и оставить пробел
        min_symbols_per_gap = 3
        
        # Вычисляем масштабный коэффициент - сколько символов на единицу времени
        # Начинаем с оценки необходимой длины
        total_notes = len(all_notes)
        scale_factor = (total_notes * min_symbols_per_gap) / duration
        
        # Не создаем слишком длинные табулатуры, но без искусственных ограничений
        display_length = int(duration * scale_factor)
        if display_length > 5000:  # Только очень большие файлы ограничиваем
            display_length = 5000
        
        # Минимальная длина табулатуры - 80 символов
        display_length = max(80, display_length)

        # Создаем пустые строки для каждой струны
        string_content = ["-" * display_length for _ in range(6)]

        # Для каждой струны создаем список занятых позиций и значений ладов
        # Отслеживаем позиции и двухзначные числа
        occupied_positions = {i: {} for i in range(1, 7)}

        # Размещаем каждую ноту в соответствии с её временем
        for note in all_notes:
            # Проверяем, что струна в допустимом диапазоне (1-6)
            if not (1 <= note.string <= 6):
                continue
                
            # Вычисляем позицию ноты на основе времени
            position = int((note.start_time - start_time) * scale_factor)
            
            # Убедимся, что позиция в допустимых пределах
            if not (0 <= position < display_length - 2):  # Оставляем место для краев
                continue
                
            string_idx = note.string - 1
            fret_num = note.fret
            fret_str = str(fret_num)
            
            # Проверяем занятость позиций
            # Ищем свободное место поблизости
            original_position = position
            max_offset = 5  # Максимально допустимое смещение
            
            # Проверяем, сколько позиций нам нужно
            positions_needed = len(fret_str)
            
            # Пробуем найти подходящее место для ноты
            found_position = False
            
            for offset in range(0, max_offset + 1):
                # Пробуем смещение вправо
                right_pos = original_position + offset
                if right_pos + positions_needed <= display_length and self._is_position_free(occupied_positions, note.string, right_pos, positions_needed):
                    position = right_pos
                    found_position = True
                    break
                    
                # Пробуем смещение влево
                left_pos = original_position - offset
                if left_pos >= 0 and self._is_position_free(occupied_positions, note.string, left_pos, positions_needed):
                    position = left_pos
                    found_position = True
                    break
            
            # Если не нашли места, пропускаем ноту
            if not found_position:
                continue
            
            # Отмечаем позиции как занятые
            for i in range(positions_needed):
                occupied_positions[note.string][position + i] = fret_num
            
            # Записываем значение лада в табулатуру
            s = list(string_content[string_idx])
            
            # Размещаем цифры в табулатуре
            for i, digit in enumerate(fret_str):
                s[position + i] = digit
                
            string_content[string_idx] = ''.join(s)
        
        string_names = ['e', 'B', 'G', 'D', 'A', 'E']
        
        # Инициализируем список для результата
        result = []
        
        for i in range(6):
            result.append(f"{string_names[i]}|{string_content[i]}|")

        return "\n".join(result)
            
    def _is_position_free(self, occupied_positions, string, start_pos, positions_needed):
        """Проверяет, свободны ли позиции в табулатуре"""
        if start_pos < 0:
            return False
            
        for i in range(positions_needed):
            if start_pos + i in occupied_positions[string]:
                return False
                
        return True


def convert_midi_to_tab(midi_file_path: str) -> Tablature:
    """Конвертировать MIDI-файл в табулатуру."""
    midi_file = mido.MidiFile(midi_file_path)
    tablature = Tablature()
    current_time = 0.0
    ticks_per_beat = midi_file.ticks_per_beat

    tempo = 120

    for track in midi_file.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = round(60000000 / msg.tempo)
                break

    for track in midi_file.tracks:
        for msg in track:
            current_time += msg.time / ticks_per_beat

            if msg.type == 'note_on' and msg.velocity > 0:
                if msg.note in GUITAR_MAPPING:
                    string, fret = GUITAR_MAPPING[msg.note]
                    duration = 0.25

                    tab_note = TabNote(string, fret, duration,
                                       current_time, tempo=tempo)
                    tablature.add_note(tab_note)

    return tablature


"""Модуль для конвертации MIDI-файлов в табулатуры."""


def midi_to_tablature(midi_file_path: str, project_tempo: int = 120) -> Tablature:
    """Конвертировать MIDI-файл в табулатуру с учетом темпа проекта.

    Args:
        midi_file_path: Путь к MIDI-файлу
        project_tempo: Темп проекта (BPM)

    Returns:
        Tablature: Объект табулатуры
    """
    tablature = convert_midi_to_tab(midi_file_path)

    # Устанавливаем темп проекта для всех нот в табулатуре
    for measure in tablature.measures:
        for note in measure:
            note.tempo = project_tempo

    return tablature


def get_text(tablature: Tablature) -> str:
    """Получить текстовое представление табулатуры.

    Args:
        tablature: Объект табулатуры

    Returns:
        str: Текстовое представление табулатуры
    """
    return tablature.to_text()


def create_empty_tablature(width: int = 80) -> str:
    """Создает пустую табулатуру заданной ширины.
    
    Args:
        width: Ширина табулатуры в символах
        
    Returns:
        str: Текстовое представление пустой табулатуры
    """
    # Ограничиваем ширину, чтобы избежать слишком длинных или коротких табулатур
    width = max(40, min(width, 200))
    
    # Создаем пустые строки для каждой струны
    string_content = ["-" * width for _ in range(6)]
    
    # Добавляем названия струн
    string_names = ['e', 'B', 'G', 'D', 'A', 'E']
    
    # Создаем форматированную табулатуру
    result = []
    for i in range(6):
        result.append(f"{string_names[i]}|{string_content[i]}|")
    
    return "\n".join(result)

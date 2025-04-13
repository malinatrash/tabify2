
from typing import Dict, List, Tuple, Optional
import mido
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
        self.measures = []
        self.current_measure = []
        self.measure_duration = 4.0  # По умолчанию 4/4
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
    
    def to_json(self) -> dict:
        """Преобразовать табулатуру в JSON формат для отображения."""
        self.finalize()
        
        tab_data = {
            "title": "Guitar Tab",
            "strings": [
                {"name": "e", "notes": []},  # 1-я струна (высокая E)
                {"name": "B", "notes": []},  # 2-я струна
                {"name": "G", "notes": []},  # 3-я струна
                {"name": "D", "notes": []},  # 4-я струна
                {"name": "A", "notes": []},  # 5-я струна
                {"name": "E", "notes": []}   # 6-я струна (низкая E)
            ]
        }
        
        # Группируем ноты по тактам для более компактного отображения
        for measure_idx, measure in enumerate(self.measures):
            if not measure:
                continue
                
            measure.sort(key=lambda x: x.start_time)
            base_position = measure_idx * 12  # Уменьшенная фиксированная длина такта
            
            for note in measure:
                # Вычисляем относительную позицию внутри такта
                relative_pos = int((note.start_time - measure[0].start_time) * 8 / self.measure_duration)
                position = base_position + relative_pos
                
                # Добавляем ноту в соответствующую струну
                tab_data["strings"][note.string - 1]["notes"].append({
                    "position": position,
                    "fret": note.fret
                })
        
        return tab_data

def convert_midi_to_tab(midi_file_path: str) -> Tablature:
    """Конвертировать MIDI-файл в табулатуру."""
    midi_file = mido.MidiFile(midi_file_path)
    tablature = Tablature()
    current_time = 0.0
    ticks_per_beat = midi_file.ticks_per_beat
    
    for track in midi_file.tracks:
        for msg in track:
            current_time += msg.time / ticks_per_beat
            
            if msg.type == 'note_on' and msg.velocity > 0:
                if msg.note in GUITAR_MAPPING:
                    string, fret = GUITAR_MAPPING[msg.note]
                    duration = 0.25  # Фиксированная длительность для упрощения
                    tab_note = TabNote(string, fret, duration, current_time)
                    tablature.add_note(tab_note)
    
    return tablature

"""Модуль для конвертации MIDI-файлов в табулатуры."""

def midi_to_tablature(midi_file_path: str) -> Tablature:
    """Конвертировать MIDI-файл в табулатуру.
    
    Args:
        midi_file_path: Путь к MIDI-файлу
        
    Returns:
        Tablature: Объект табулатуры
    """
    return convert_midi_to_tab(midi_file_path)

def save_tablature(tablature: Tablature, output_path: str) -> None:
    """Сохранить табулатуру в JSON-файл.
    
    Args:
        tablature: Объект табулатуры
        output_path: Путь для сохранения JSON-файла
    """
    import json
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tablature.to_json(), f, ensure_ascii=False, indent=2)

-- Создание таблицы tablatures если она не существует
CREATE TABLE IF NOT EXISTS tablatures (
    id SERIAL PRIMARY KEY,
    midi_file_id INTEGER REFERENCES midi_files(id),
    tab_data JSONB NOT NULL,
    tab_text TEXT,
    is_edited BOOLEAN DEFAULT FALSE,
    last_edited_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Добавление индекса для улучшения производительности
CREATE INDEX IF NOT EXISTS idx_tablatures_midi_file_id ON tablatures(midi_file_id);

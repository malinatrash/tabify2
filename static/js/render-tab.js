/**
 * Функция для отрисовки табулатуры из JSON-данных
 */

document.addEventListener('DOMContentLoaded', function() {
    // Находим все элементы с табулатурами
    const tabElements = document.querySelectorAll('.tablature-display[data-tab-data]');
    
    tabElements.forEach(element => {
        try {
            // Получаем JSON-данные табулатуры
            const tabData = JSON.parse(element.getAttribute('data-tab-data'));
            
            // Создаем HTML-представление табулатуры
            const tabHTML = renderTabFromJSON(tabData);
            
            // Вставляем HTML в элемент
            element.innerHTML = tabHTML;
        } catch (error) {
            console.error('Ошибка при отрисовке табулатуры:', error);
            element.innerHTML = '<p class="text-danger">Ошибка при отрисовке табулатуры</p>';
        }
    });
});

/**
 * Преобразует JSON-данные табулатуры в HTML
 * @param {Object} tabData - JSON-данные табулатуры
 * @returns {string} HTML-представление табулатуры
 */
function renderTabFromJSON(tabData) {
    // Проверяем базовую структуру данных
    if (!tabData || typeof tabData !== 'object') {
        throw new Error('Некорректные данные табулатуры: данные отсутствуют или имеют неверный формат');
    }

    // Проверяем наличие и формат массива strings
    if (!tabData.strings || !Array.isArray(tabData.strings) || tabData.strings.length === 0) {
        throw new Error('Некорректные данные табулатуры: отсутствует или пуст массив strings');
    }

    // Проверяем структуру каждой строки
    for (const string of tabData.strings) {
        if (!string.name || typeof string.name !== 'string') {
            throw new Error('Некорректные данные табулатуры: отсутствует или неверный формат name для строки');
        }
        if (!Array.isArray(string.notes)) {
            throw new Error('Некорректные данные табулатуры: отсутствует или неверный формат массива notes');
        }
        for (const note of string.notes) {
            if (typeof note.position !== 'number' || typeof note.fret !== 'number') {
                throw new Error('Некорректные данные табулатуры: неверный формат position или fret для ноты');
            }
        }
    }
    
    let html = '<pre class="tab-notation">';
    
    // Добавляем заголовок табулатуры
    if (tabData.title) {
        html += `${tabData.title}\n`;
    }
    
    // Отрисовываем строки табулатуры
    tabData.strings.forEach((string, index) => {
        html += `${string.name}|`;
        
        // Находим максимальную позицию для определения длины табулатуры
        const maxPosition = Math.max(...string.notes.map(note => note.position), 12);
        
        // Создаем массив для хранения символов строки
        const lineChars = new Array(maxPosition + 4).fill('-');
        
        // Расставляем ноты
        string.notes.forEach(note => {
            // Добавляем ноту в соответствующую позицию
            lineChars[note.position] = note.fret.toString().padStart(2, '0');
        });
        
        // Добавляем разделители тактов
        for (let i = 12; i < lineChars.length; i += 12) {
            lineChars[i] = '|';
        }
        
        // Собираем строку из символов и добавляем конечный разделитель
        html += lineChars.join('');
        html += '||\n';
    });
    
    html += '</pre>';
    return html;
}
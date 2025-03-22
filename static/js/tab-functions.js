/**
 * Функции для работы с табулатурами
 */

// Сообщаем, что файл успешно загружен
console.log('Файл tab-functions.js загружен!');

/**
 * Генерирует табулатуру для MIDI-файла
 * @param {string} projectId - ID проекта
 * @param {string} midiId - ID MIDI-файла
 */
function generateTab(projectId, midiId) {
    console.log(`Генерируем табулатуру для проекта ${projectId}, MIDI ${midiId}`);
    
    // Показываем индикатор загрузки и блокируем кнопку
    const generateBtn = document.getElementById('generateTabBtn');
    if (generateBtn) {
        generateBtn.disabled = true;
    }
    
    const loadingElement = document.getElementById('loadingTab');
    if (loadingElement) {
        loadingElement.style.display = 'block';
    }
    
    const errorElement = document.getElementById('tabError');
    if (errorElement) {
        errorElement.style.display = 'none';
    }
    
    // Отправляем запрос на генерацию табулатуры
    fetch(`/projects/${projectId}/midi/${midiId}/tab/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.error || 'Ошибка при генерации табулатуры');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Табулатура успешно сгенерирована:', data.message);
        // Перенаправляем на страницу с табулатурой
        window.location.href = `/projects/${projectId}/midi/${midiId}/tab/view`;
    })
    .catch(error => {
        console.error('Ошибка генерации табулатуры:', error.message);
        // Показываем ошибку
        if (generateBtn) {
            generateBtn.disabled = false;
        }
        
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
        
        if (errorElement) {
            errorElement.style.display = 'block';
            const errorTextElement = document.getElementById('errorText');
            if (errorTextElement) {
                errorTextElement.textContent = error.message;
            }
        }
    });
}

/**
 * Сохраняет отредактированную табулатуру
 * @param {string} projectId - ID проекта
 * @param {string} midiId - ID MIDI-файла
 * @param {object} tabData - Данные табулатуры
 * @returns {Promise} - Promise с результатом сохранения
 */
function saveTabChanges(projectId, midiId, tabData) {
    return fetch(`/projects/${projectId}/midi/${midiId}/tab/update`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(tabData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.error || 'Ошибка при сохранении табулатуры');
            });
        }
        return response.json();
    });
}

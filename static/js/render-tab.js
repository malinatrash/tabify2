/**
 * Функция для отрисовки и редактирования табулатуры из текстового представления
 */

document.addEventListener('DOMContentLoaded', function () {
	// Находим все элементы с табулатурами
	const tabContentElements = document.querySelectorAll('.tablature-content');

	tabContentElements.forEach(element => {
		try {
			// Получаем текстовые данные табулатуры
			const tabText = element.getAttribute('data-tab-text');
			if (!tabText) {
				console.warn('Текст табулатуры не найден');
				element.innerHTML = '<p class="text-warning">Табулатура не доступна</p>';
				return;
			}

			// Получаем MIDI ID
			const trackRow = element.closest('.track-row');
			let midiId = element.getAttribute('data-midi-id');
			
			if (!midiId && trackRow) {
				midiId = trackRow.getAttribute('data-midi-id');
				console.log('Найден MIDI ID для табулатуры:', midiId);
			}

			// Создаем HTML представление для редактирования
			const tabHTML = renderTabFromText(tabText, midiId);

			// Вставляем HTML
			element.innerHTML = tabHTML;

			// Инициализируем отслеживание изменений
			initTabEditing();
		} catch (error) {
			console.error('Ошибка при отрисовке табулатуры:', error);
			element.innerHTML =
				'<p class="text-danger">Ошибка при отрисовке табулатуры</p>';
		}
	});
});

/**
 * Преобразует текстовое представление табулатуры в HTML для редактирования
 * @param {string} tabText - Текстовое представление табулатуры
 * @param {string} midiId - ID MIDI файла
 * @returns {string} HTML-представление табулатуры
 */
function renderTabFromText(tabText, midiId) {
	if (!tabText) {
		return '<p class="text-warning">Табулатура не доступна</p>';
	}

	// Сохраняем оригинальный текст для сравнения при редактировании
	window.originalTabText = tabText;

	// Получаем ID проекта из URL
	const projectId = window.location.pathname.split('/')[2];

	// Создаем HTML с предварительно отформатированным текстом, сохраняя все пробелы и переносы строк
	// contenteditable позволяет редактировать содержимое
	const html = `<pre class="tab-notation" contenteditable="true" data-midi-id="${midiId || ''}" data-project-id="${projectId}">${tabText}</pre>`;

	return html;
}

/**
 * Инициализирует отслеживание изменений в табулатуре
 */
function initTabEditing() {
	const tabElements = document.querySelectorAll('.tab-notation[contenteditable="true"]');
	console.log('Найдено', tabElements.length, 'элементов табулатуры для редактирования');

	tabElements.forEach(element => {
		// Для каждого элемента создаем свой таймер
		let updateTimer = null;

		// Добавляем обработчики событий для отслеживания изменений
		element.addEventListener('input', () => {
			// Сбрасываем предыдущий таймер при новом вводе
			clearTimeout(updateTimer);

			// Устанавливаем новый таймер на 5 секунд
			updateTimer = setTimeout(() => {
				// Если пользователь не вносил изменения в течение 5 секунд, отправляем данные
				const midiId = element.getAttribute('data-midi-id');
				const projectId = element.getAttribute('data-project-id') || window.location.pathname.split('/')[2];

					// Текущее содержимое табулатуры
				const updatedTabText = element.textContent;

				// Проверяем, были ли изменения
				if (updatedTabText !== window.originalTabText) {
					// Проверяем валидность табулатуры
					const validationResult = validateTabText(updatedTabText, window.originalTabText);
					
					if (!validationResult.isValid) {
						// Если табулатура невалидна, показываем ошибку и возвращаем оригинальный текст
						showNotification(`Ошибка валидации: ${validationResult.error}`, 'error');
						// Восстанавливаем оригинальный текст
						element.textContent = window.originalTabText;
						return;
					}
					
					console.log('Отправка обновленной табулатуры для MIDI:', midiId);
					
					// Отправляем обновление через WebSocket, если он доступен
					if (window.tabWebSocket) {
						window.tabWebSocket.sendTabUpdate(updatedTabText, midiId);
					}
					
					// Также отправляем на сервер для сохранения
					updateTabOnServer(projectId, midiId, updatedTabText);
				}
			}, 5000); // 5 секунд
		});

		// Отслеживаем, когда пользователь заканчивает редактирование (кликает вне элемента)
		document.addEventListener('click', e => {
			if (!element.contains(e.target) && updateTimer) {
				clearTimeout(updateTimer);

				// Текущее содержимое табулатуры
				const midiId = element.getAttribute('data-midi-id');
				const projectId = element.getAttribute('data-project-id') || window.location.pathname.split('/')[2];
				const updatedTabText = element.textContent;

				// Проверяем, были ли изменения
				if (updatedTabText !== window.originalTabText) {
					console.log('Отправка обновленной табулатуры после клика для MIDI:', midiId);
					updateTabOnServer(projectId, midiId, updatedTabText);
				}
			}
		});
	});
}

/**
 * Отправляет обновленные данные табулатуры на сервер
 * @param {string} projectId - ID проекта
 * @param {string} midiId - ID MIDI файла
 * @param {string} tabText - Текст табулатуры
 */
async function updateTabOnServer(projectId, midiId, tabText) {
	// Проверяем, что midiId не пустой
	if (!midiId) {
		console.error('Ошибка: midi ID не указан');
		showNotification('Невозможно обновить табулатуру: midi ID не указан', 'error');
		return;
	}

	try {
		// Формируем URL (исправлен на существующий эндпоинт)
		const url = `/projects/${projectId}/midi/${midiId}/tab`;
		console.log(`Отправка запроса на URL: ${url} с midiId = ${midiId}`);

		// Формируем данные для отправки
		const tabData = {
			tab_text: tabText,
			midi_id: midiId,
			is_edited: true,
			timestamp: new Date().getTime()
		};

		const response = await fetch(url, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(tabData),
		});

		const result = await response.json();

		if (response.ok) {
			console.log(`Табулатура для MIDI ${midiId} успешно обновлена:`, result.message);
			// Обновляем оригинальный текст
			window.originalTabText = tabText;
			// Показываем уведомление
			showNotification('Табулатура успешно обновлена', 'success');
		} else {
			console.error(`Ошибка при обновлении табулатуры ${midiId}:`, result.error);
			showNotification('Ошибка при обновлении табулатуры: ' + result.error, 'error');
		}
	} catch (error) {
		console.error(`Ошибка при отправке запроса для MIDI ${midiId}:`, error);
		showNotification('Ошибка при отправке запроса: ' + error.message, 'error');
	}
}

/**
 * Валидирует текстовое представление табулатуры
 * @param {string} tabText - Новый текст табулатуры
 * @param {string} originalText - Оригинальный текст табулатуры для сравнения
 * @returns {Object} Результат валидации {isValid: boolean, error: string}
 */
function validateTabText(tabText, originalText) {
	// Проверяем, что количество строк не уменьшилось (нельзя удалять строки)
	const originalLines = originalText.split('\n');
	const newLines = tabText.split('\n');
	
	if (newLines.length < originalLines.length) {
		return {
			isValid: false,
			error: 'Удаление строк не разрешено. Вы удалили ' + (originalLines.length - newLines.length) + ' строк'
		};
	}
	
	// Проверка струнных обозначений
	// Допустимые символы в табулатуре: цифры, символы |<>-, струны (e,B,G,D,A,E), и специальные обозначения
	// Регулярное выражение для строки струны
	const stringLineRegex = /^[eE]\|[-0-9hpb\/\\xrs]*\|$/;
	const stringLineBRegex = /^[bB]\|[-0-9hpb\/\\xrs]*\|$/;
	const stringLineGRegex = /^[gG]\|[-0-9hpb\/\\xrs]*\|$/;
	const stringLineDRegex = /^[dD]\|[-0-9hpb\/\\xrs]*\|$/;
	const stringLineARegex = /^[aA]\|[-0-9hpb\/\\xrs]*\|$/;
	const stringLineELowRegex = /^[eE]\|[-0-9hpb\/\\xrs]*\|$/;
	
	// Проверяем каждую строку, начиная с шапки табулатуры
	for (let i = 0; i < newLines.length; i++) {
		const line = newLines[i].trim();
		
		// Пропускаем пустые строки или строки с комментариями
		if (line === '' || line.startsWith('//') || line.startsWith('#')) {
			continue;
		}
		
		// Проверяем строки с обозначением струн
		if (line.startsWith('e|') || line.startsWith('E|')) {
			if (!stringLineRegex.test(line)) {
				return {
					isValid: false,
					error: `Неверный формат верхней струны e в строке ${i+1}: "${line}"`
				};
			}
		} else if (line.startsWith('B|') || line.startsWith('b|')) {
			if (!stringLineBRegex.test(line)) {
				return {
					isValid: false,
					error: `Неверный формат струны B в строке ${i+1}: "${line}"`
				};
			}
		} else if (line.startsWith('G|') || line.startsWith('g|')) {
			if (!stringLineGRegex.test(line)) {
				return {
					isValid: false,
					error: `Неверный формат струны G в строке ${i+1}: "${line}"`
				};
			}
		} else if (line.startsWith('D|') || line.startsWith('d|')) {
			if (!stringLineDRegex.test(line)) {
				return {
					isValid: false,
					error: `Неверный формат струны D в строке ${i+1}: "${line}"`
				};
			}
		} else if (line.startsWith('A|') || line.startsWith('a|')) {
			if (!stringLineARegex.test(line)) {
				return {
					isValid: false,
					error: `Неверный формат струны A в строке ${i+1}: "${line}"`
				};
			}
		} else if (line.startsWith('E|') || line.startsWith('e|')) {
			if (!stringLineELowRegex.test(line)) {
				return {
					isValid: false,
					error: `Неверный формат нижней струны E в строке ${i+1}: "${line}"`
				};
			}
		}
		
		// Проверка на недопустимые символы в табулатуре
		if (/[^a-zA-Z0-9|\-\/\\phbxrs\s\n\t]/.test(line)) {
			return {
				isValid: false,
				error: `Недопустимые символы в строке ${i+1}: "${line}"`
			};
		}
	}
	
	// Все проверки пройдены, табулатура валидна
	return {
		isValid: true,
		error: ''
	};
}

/**
 * Показывает уведомление
 * @param {string} message - Текст уведомления
 * @param {string} type - Тип уведомления ('info', 'success', 'error')
 */
function showNotification(message, type = 'info') {
	// Проверяем, существует ли уже контейнер для уведомлений
	let notificationsContainer = document.getElementById('notifications-container');

	if (!notificationsContainer) {
		// Создаем контейнер, если он не существует
		notificationsContainer = document.createElement('div');
		notificationsContainer.id = 'notifications-container';
		notificationsContainer.style.position = 'fixed';
		notificationsContainer.style.bottom = '20px';
		notificationsContainer.style.right = '20px';
		notificationsContainer.style.zIndex = '9999';
		document.body.appendChild(notificationsContainer);
	}

	// Создаем элемент уведомления
	const notification = document.createElement('div');
	notification.className = `notification notification-${type}`;
	notification.innerHTML = `
		<div class="notification-content">
			<span>${message}</span>
			<button class="notification-close">&times;</button>
		</div>
	`;

	// Стилизуем уведомление
	notification.style.backgroundColor =
		type === 'error' ? 'rgba(255, 70, 70, 0.8)' : 'rgba(50, 205, 50, 0.8)';
	notification.style.color = 'white';
	notification.style.padding = '10px 15px';
	notification.style.borderRadius = '5px';
	notification.style.marginTop = '10px';
	notification.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.2)';
	notification.style.backdropFilter = 'blur(5px)';
	notification.style.webkitBackdropFilter = 'blur(5px)';
	notification.style.animation = 'notification-fade-in 0.3s';

	// Добавляем уведомление в контейнер
	notificationsContainer.appendChild(notification);

	// Добавляем обработчик для кнопки закрытия
	const closeButton = notification.querySelector('.notification-close');
	closeButton.style.background = 'none';
	closeButton.style.border = 'none';
	closeButton.style.color = 'white';
	closeButton.style.fontSize = '20px';
	closeButton.style.marginLeft = '10px';
	closeButton.style.cursor = 'pointer';
	closeButton.addEventListener('click', () => {
		notification.remove();
	});

	// Автоматически скрываем уведомление через 5 секунд
	setTimeout(() => {
		notification.style.animation = 'notification-fade-out 0.3s';
		notification.addEventListener('animationend', () => {
			notification.remove();
		});
	}, 5000);
}
/**
 * Функция для отрисовки табулатуры из JSON-данных
 */

document.addEventListener('DOMContentLoaded', function () {
	// Находим все элементы с табулатурами
	const tabContentElements = document.querySelectorAll('.tablature-content[data-tab-data]')

	tabContentElements.forEach(element => {
		try {
			// Получаем JSON-данные табулатуры
			const tabData = JSON.parse(element.getAttribute('data-tab-data'))

			// Получаем MIDI ID из родительского элемента
			const trackRow = element.closest('.track-row')
			if (trackRow) {
				const midiId = trackRow.getAttribute('data-midi-id')
				console.log('Найден MIDI ID для табулатуры:', midiId)
				
				// Добавляем MIDI ID в данные табулатуры
				tabData.midi_id = midiId
			}

			// Создаем HTML-представление табулатуры
			const tabHTML = renderTabFromJSON(tabData)

			// Вставляем HTML в элемент
			element.innerHTML = tabHTML
		} catch (error) {
			console.error('Ошибка при отрисовке табулатуры:', error)
			element.innerHTML =
				'<p class="text-danger">Ошибка при отрисовке табулатуры</p>'
		}
	})
})

/**
 * Преобразует JSON-данные табулатуры в HTML
 * @param {Object} tabData - JSON-данные табулатуры
 * @returns {string} HTML-представление табулатуры
 */
function renderTabFromJSON(tabData) {
	// Проверяем базовую структуру данных
	if (!tabData || typeof tabData !== 'object') {
		throw new Error(
			'Некорректные данные табулатуры: данные отсутствуют или имеют неверный формат'
		)
	}

	// Сохраняем оригинальные данные для сравнения при редактировании
	window.originalTabData = JSON.parse(JSON.stringify(tabData))

	// Проверяем наличие и формат массива strings
	if (
		!tabData.strings ||
		!Array.isArray(tabData.strings) ||
		tabData.strings.length === 0
	) {
		throw new Error(
			'Некорректные данные табулатуры: отсутствует или пуст массив strings'
		)
	}

	// Проверяем структуру каждой строки
	for (const string of tabData.strings) {
		if (!string.name || typeof string.name !== 'string') {
			throw new Error(
				'Некорректные данные табулатуры: отсутствует или неверный формат name для строки'
			)
		}
		if (!Array.isArray(string.notes)) {
			throw new Error(
				'Некорректные данные табулатуры: отсутствует или неверный формат массива notes'
			)
		}
		for (const note of string.notes) {
			if (typeof note.position !== 'number' || typeof note.fret !== 'number') {
				throw new Error(
					'Некорректные данные табулатуры: неверный формат position или fret для ноты'
				)
			}
		}
	}

	let html =
		'<pre class="tab-notation" contenteditable="true" data-midi-id="' +
		(tabData.midi_id || '') +
		'" data-project-id="' +
		(tabData.project_id || window.location.pathname.split('/')[2]) +
		'">'

	// Отрисовываем строки табулатуры
	tabData.strings.forEach((string, index) => {
		html += `${string.name}|`

		// Находим максимальную позицию для определения длины табулатуры
		const maxPosition = Math.max(...string.notes.map(note => note.position), 12)

		// Создаем массив для хранения символов строки
		const lineChars = new Array(maxPosition + 4).fill('-')

		// Расставляем ноты
		string.notes.forEach(note => {
			// Добавляем ноту в соответствующую позицию
			lineChars[note.position] = note.fret.toString().padStart(2, '0')
		})

		// Собираем строку из символов и добавляем конечный разделитель
		html += lineChars.join('')
		html += '||\n'
	})

	html += '</pre>'
	return html
}

// Функция для парсинга текста табулатуры и извлечения нот
function parseTabContent(content, originalData) {
	// Создаем копию оригинальных данных
	const updatedData = JSON.parse(JSON.stringify(originalData))

	// Разбиваем текст по строкам
	const lines = content.trim().split('\n')
	console.log('Строки табулатуры для парсинга:', lines)
	
	// Обрабатываем каждую строку
	lines.forEach((line, index) => {
		// Проверяем, что у нас есть соответствующая строка в данных
		if (index < updatedData.strings.length) {
			// Парсим строку
			const parts = line.split('|')
			
			// Если строка содержит хотя бы один разделитель
			if (parts.length > 0) {
				// Извлекаем название струны
				const stringName = parts[0].trim()
				if (stringName) {
					// Обновляем название струны
					updatedData.strings[index].name = stringName
				}
				
				// Если есть содержимое после вертикальной черты
				if (parts.length > 1) {
					// Обновляем ноты для этой строки
					// Отладочный комментарий - сохраняем оригинальные ноты
					console.log(`Обновлена строка ${index}: ${stringName} | ${parts[1]}`)
				}
			}
		}
	})
	
	// Добавляем поле для отметки, что данные были изменены
	updatedData.edited = true
	
	// Добавляем дату изменения
	updatedData.last_edited = new Date().getTime()
	
	// Запоминаем midiId в новых данных
	if (window.currentMidiId) {
		updatedData.midi_id = window.currentMidiId
	}
	
	return updatedData
}

// Функция для инициализации отслеживания изменений в табулатуре
function initTabEditing() {
	const tabElements = document.querySelectorAll(
		'.tab-notation[contenteditable="true"]'
	)
	console.log('Найдено', tabElements.length, 'элементов табулатуры для редактирования')

	tabElements.forEach(element => {
		// Для каждого элемента создаем свой таймер
		let updateTimer = null
		
		// Находим midi_id для этого элемента табулатуры
		let tabMidiId = null
		
		// Пытаемся найти родительский элемент с data-midi-id
		const trackRow = element.closest('.track-row')
		if (trackRow) {
			tabMidiId = trackRow.getAttribute('data-midi-id')
			console.log('Найден midi_id для табулатуры:', tabMidiId)
			
			// Добавляем атрибут напрямую к элементу табулатуры
			element.setAttribute('data-midi-id', tabMidiId)
		}
		
		// Добавляем обработчики событий для отслеживания изменений
		element.addEventListener('input', () => {
			// Сбрасываем предыдущий таймер при новом вводе
			clearTimeout(updateTimer)

			// Устанавливаем новый таймер на 5 секунд
			updateTimer = setTimeout(() => {
				// Если пользователь не вносил изменения в течение 5 секунд, отправляем данные
				// Берем midi_id из атрибута элемента
				const midiId = element.getAttribute('data-midi-id')
				const projectId = window.location.pathname.split('/')[2] // Получаем ID проекта из URL

				// Используем функцию парсинга для получения обновленных данных
				const updatedTabData = parseTabContent(element.textContent, window.originalTabData)
				
				console.log('Sending updated tablature for MIDI:', midiId)
				// Отправляем данные на сервер
				updateTabOnServer(projectId, midiId, updatedTabData)
			}, 5000) // 5 секунд
		})

		// Также отслеживаем, когда пользователь заканчивает редактирование (кликает вне элемента)
		document.addEventListener('click', e => {
			if (!element.contains(e.target) && updateTimer) {
				clearTimeout(updateTimer)

				// Берем midi_id из атрибута элемента
				const midiId = element.getAttribute('data-midi-id')
				const projectId = window.location.pathname.split('/')[2]

				// Используем функцию парсинга для получения обновленных данных
				const updatedTabData = parseTabContent(element.textContent, window.originalTabData)
				
				console.log('Sending updated tablature (click) for MIDI:', midiId)
				// Отправляем данные на сервер
				updateTabOnServer(projectId, midiId, updatedTabData)
			}
		})
	})
}

// Функция для отправки обновленных данных табулатуры на сервер
async function updateTabOnServer(projectId, midiId, tabData) {
	// Проверяем, что midiId не пустой
	if (!midiId) {
		// Пытаемся найти midiId из табулатуры, которую редактируем
		const activeTab = document.activeElement
		if (activeTab && activeTab.classList.contains('tab-notation')) {
			// Пытаемся найти родительский элемент с data-midi-id
			const trackRow = activeTab.closest('.track-row')
			if (trackRow) {
				midiId = trackRow.getAttribute('data-midi-id')
				console.log('Найден midiId из родительского элемента:', midiId)
			}
		}
		
		// Если все еще нет midiId, сообщаем об ошибке
		if (!midiId) {
			console.error('Ошибка: midi ID не указан')
			showNotification(
				'Невозможно обновить табулатуру: midi ID не указан',
				'error'
			)
			return
		}
	}

	// Убедимся, что у нас есть midi_id в данных
	tabData.midi_id = midiId

	try {
		// Формируем URL без двойных слэшей
		const url = `/projects/${projectId}/midi/${midiId}/tab/update`
		console.log(`Отправка запроса на URL: ${url} с midiId = ${midiId}`)
		
		// Маркируем, что данные были изменены ручным редактированием 
		tabData.is_edited = true
		tabData.timestamp = new Date().getTime()
		
		const response = await fetch(url, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(tabData),
		})

		const result = await response.json()

		if (response.ok) {
			console.log(`Табулатура для MIDI ${midiId} успешно обновлена:`, result.message)
			// Показываем уведомление об успешном обновлении
			showNotification('Табулатура успешно обновлена', 'success')
		} else {
			console.error(`Ошибка при обновлении табулатуры ${midiId}:`, result.error)
			showNotification(
				'Ошибка при обновлении табулатуры: ' + result.error,
				'error'
			)
		}
	} catch (error) {
		console.error(`Ошибка при отправке запроса для MIDI ${midiId}:`, error)
		showNotification('Ошибка при отправке запроса: ' + error.message, 'error')
	}
}

// Функция для отображения уведомлений
function showNotification(message, type = 'info') {
	// Проверяем, существует ли уже контейнер для уведомлений
	let notificationsContainer = document.getElementById(
		'notifications-container'
	)

	if (!notificationsContainer) {
		// Создаем контейнер, если он не существует
		notificationsContainer = document.createElement('div')
		notificationsContainer.id = 'notifications-container'
		notificationsContainer.style.position = 'fixed'
		notificationsContainer.style.bottom = '20px'
		notificationsContainer.style.right = '20px'
		notificationsContainer.style.zIndex = '9999'
		document.body.appendChild(notificationsContainer)
	}

	// Создаем элемент уведомления
	const notification = document.createElement('div')
	notification.className = `notification notification-${type}`
	notification.innerHTML = `
		<div class="notification-content">
			<span>${message}</span>
			<button class="notification-close">&times;</button>
		</div>
	`

	// Стилизуем уведомление
	notification.style.backgroundColor =
		type === 'error' ? 'rgba(255, 70, 70, 0.8)' : 'rgba(50, 205, 50, 0.8)'
	notification.style.color = 'white'
	notification.style.padding = '10px 15px'
	notification.style.borderRadius = '5px'
	notification.style.marginTop = '10px'
	notification.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.2)'
	notification.style.backdropFilter = 'blur(5px)'
	notification.style.webkitBackdropFilter = 'blur(5px)'
	notification.style.animation = 'notification-fade-in 0.3s'

	// Добавляем уведомление в контейнер
	notificationsContainer.appendChild(notification)

	// Добавляем обработчик для кнопки закрытия
	const closeButton = notification.querySelector('.notification-close')
	closeButton.style.background = 'none'
	closeButton.style.border = 'none'
	closeButton.style.color = 'white'
	closeButton.style.fontSize = '20px'
	closeButton.style.marginLeft = '10px'
	closeButton.style.cursor = 'pointer'
	closeButton.addEventListener('click', () => {
		notification.remove()
	})

	// Автоматически скрываем уведомление через 5 секунд
	setTimeout(() => {
		notification.style.animation = 'notification-fade-out 0.3s'
		notification.addEventListener('animationend', () => {
			notification.remove()
		})
	}, 5000)
}

// Инициализируем отслеживание изменений после загрузки страницы
document.addEventListener('DOMContentLoaded', function () {
	// Отложенный запуск, чтобы убедиться, что все табулатуры отрисованы
	setTimeout(initTabEditing, 500)
})

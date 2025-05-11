/**
 * tab-websocket.js
 * Управление WebSocket-соединением для совместного редактирования табулатуры
 */

class TabWebSocket {
	constructor() {
		this.socket = null
		this.projectId = null
		this.midiId = null
		this.clientId = this.generateClientId()
		this.reconnectAttempts = 0
		this.maxReconnectAttempts = 5
		this.reconnectDelay = 3000 // 3 секунды
		this.pingInterval = null
		this.tabUpdateTimeout = null
		this.lastTabText = null
		this.onTabUpdateCallbacks = []
	}

	/**
	 * Генерирует уникальный ID клиента
	 */
	generateClientId() {
		return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
	}

	/**
	 * Подключается к WebSocket для конкретной табулатуры
	 * @param {string} projectId - ID проекта
	 * @param {string} midiId - ID MIDI файла
	 */
	connect(projectId, midiId) {
		if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
			console.log('Уже подключен к WebSocket или подключение в процессе')
			return
		}

		this.projectId = projectId
		this.midiId = midiId

		// Формируем URL для WebSocket
		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
		const wsUrl = `${protocol}//${window.location.host}/ws/project/${projectId}/tab/${midiId}?client_id=${this.clientId}`

		console.log(`Подключение к WebSocket: ${wsUrl}`)

		try {
			// Проверяем, есть ли поддержка WebSocket на сервере
			// Для тестирования временно пропускаем реальное подключение
			console.log('Пропускаем подключение WebSocket для отладки')

			// Устанавливаем режим автономной работы (без WebSocket)
			this.showConnectionStatus(false, false, true)

			/* Временно закомментировано для отладки
            this.socket = new WebSocket(wsUrl);

            // Обработчики событий WebSocket
            this.socket.onopen = this.onOpen.bind(this);
            this.socket.onmessage = this.onMessage.bind(this);
            this.socket.onclose = this.onClose.bind(this);
            this.socket.onerror = this.onError.bind(this);
            */
		} catch (error) {
			console.error('Ошибка при создании WebSocket:', error)
			this.scheduleReconnect()
		}
	}

	/**
	 * Обработчик события открытия соединения
	 */
	onOpen(event) {
		console.log('WebSocket соединение установлено')

		// Сбрасываем счетчик попыток переподключения
		this.reconnectAttempts = 0

		// Настраиваем пинг для поддержания соединения
		this.startPingInterval()

		// Уведомление в интерфейсе о подключении
		this.showConnectionStatus(true)
	}

	/**
	 * Обработчик входящих сообщений
	 */
	onMessage(event) {
		try {
			const data = JSON.parse(event.data)

			// Обрабатываем различные типы сообщений
			switch (data.type) {
				case 'tab_update':
					// Получаем обновление табулатуры от других пользователей
					this.handleTabUpdate(data)
					break

				case 'user_connected':
					console.log(`Пользователь ${data.user_id} подключился`)
					// Можно отобразить уведомление о новом пользователе
					break

				case 'user_disconnected':
					console.log(`Пользователь ${data.user_id} отключился`)
					// Можно отобразить уведомление об отключении пользователя
					break

				case 'pong':
					// Получили ответ на ping
					break

				default:
					console.log('Получено неизвестное сообщение:', data)
			}
		} catch (error) {
			console.error('Ошибка при обработке сообщения:', error)
		}
	}

	/**
	 * Обработчик закрытия соединения
	 */
	onClose(event) {
		console.log(`WebSocket соединение закрыто: ${event.reason} (${event.code})`)

		// Останавливаем пинг
		this.stopPingInterval()

		// Обновляем статус подключения в интерфейсе
		this.showConnectionStatus(false)

		// Пытаемся переподключиться
		this.scheduleReconnect()
	}

	/**
	 * Обработчик ошибок
	 */
	onError(error) {
		console.error('Ошибка WebSocket:', error)
	}

	/**
	 * Запланировать переподключение
	 */
	scheduleReconnect() {
		if (this.reconnectAttempts < this.maxReconnectAttempts) {
			console.log(
				`Попытка переподключения через ${this.reconnectDelay / 1000} сек...`
			)
			setTimeout(() => {
				this.reconnectAttempts++
				this.connect(this.projectId, this.midiId)
			}, this.reconnectDelay)
		} else {
			console.log('Достигнуто максимальное количество попыток переподключения')
			this.showConnectionStatus(false, true)
		}
	}

	/**
	 * Отобразить статус соединения
	 * @param {boolean} isConnected - Установлено ли соединение
	 * @param {boolean} isFailed - Не удалось ли подключиться
	 * @param {boolean} isOfflineMode - Работа в автономном режиме
	 */
	showConnectionStatus(isConnected, isFailed = false, isOfflineMode = false) {
		// Найдем или создадим элемент для отображения статуса
		let statusElement = document.getElementById('ws-connection-status')
		if (!statusElement) {
			statusElement = document.createElement('div')
			statusElement.id = 'ws-connection-status'
			statusElement.className = 'connection-status'

			// Добавляем элемент в DOM
			const sequencerGrid = document.querySelector('.sequencer-grid')
			if (sequencerGrid) {
				sequencerGrid.appendChild(statusElement)
			}
		}

		if (isOfflineMode) {
			// Автономный режим (без WebSocket)
			statusElement.innerHTML =
				'<span class="status-offline"><i class="fas fa-user"></i>Edit without sync</span>'
			statusElement.classList.remove('connected', 'disconnected', 'failed')
			statusElement.classList.add('offline')
			this.isOfflineMode = true
		} else if (isConnected) {
			statusElement.innerHTML =
				'<span class="status-connected"><i class="fas fa-circle"></i> Совместное редактирование активно</span>'
			statusElement.classList.remove('disconnected', 'failed', 'offline')
			statusElement.classList.add('connected')
			this.isOfflineMode = false
		} else if (isFailed) {
			statusElement.innerHTML =
				'<span class="status-failed"><i class="fas fa-exclamation-triangle"></i> Не удалось подключиться</span>'
			statusElement.classList.remove('connected', 'disconnected', 'offline')
			statusElement.classList.add('failed')
			this.isOfflineMode = true
		} else {
			statusElement.innerHTML =
				'<span class="status-disconnected"><i class="fas fa-circle"></i> Переподключение...</span>'
			statusElement.classList.remove('connected', 'failed', 'offline')
			statusElement.classList.add('disconnected')
			this.isOfflineMode = true
		}
	}

	/**
	 * Начать интервал для пинга сервера (поддержание соединения)
	 */
	startPingInterval() {
		this.stopPingInterval()
		this.pingInterval = setInterval(() => {
			if (this.socket && this.socket.readyState === WebSocket.OPEN) {
				this.socket.send(JSON.stringify({ type: 'ping' }))
			}
		}, 30000) // Пинг каждые 30 секунд
	}

	/**
	 * Остановить интервал пинга
	 */
	stopPingInterval() {
		if (this.pingInterval) {
			clearInterval(this.pingInterval)
			this.pingInterval = null
		}
	}

	/**
	 * Обрабатывает обновления табулатуры от других пользователей
	 */
	handleTabUpdate(data) {
		if (data.sender_id === this.clientId) {
			// Игнорируем собственные обновления
			return
		}

		// Находим элемент табулатуры для указанного MIDI файла
		const tabElements = document.querySelectorAll(
			`.track-row[data-midi-id="${data.midi_id}"] .tab-notation`
		)
		if (tabElements && tabElements.length > 0) {
			// Обновляем табулатуру
			tabElements.forEach(element => {
				// Сохраняем текущую позицию курсора
				const selection = window.getSelection()
				const activeElement = document.activeElement
				const isTabActive = activeElement === element
				let range = null

				if (isTabActive && selection && selection.rangeCount > 0) {
					range = selection.getRangeAt(0).cloneRange()
				}

				// Обновляем текст
				element.textContent = data.tab_text

				// Восстанавливаем позицию курсора, если элемент был активен
				if (isTabActive && range) {
					try {
						selection.removeAllRanges()
						selection.addRange(range)
					} catch (e) {
						console.warn('Не удалось восстановить позицию курсора:', e)
					}
				}
			})

			// Вызываем все зарегистрированные callbacks
			this.notifyTabUpdateCallbacks(data.tab_text, data.midi_id)
		}
	}

	/**
	 * Отправляет обновленную табулатуру на сервер
	 */
	sendTabUpdate(tabText, midiId) {
		// Проверяем, изменился ли текст табулатуры
		if (tabText === this.lastTabText) {
			return // Избегаем отправки одинаковых обновлений
		}

		this.lastTabText = tabText

		// Используем debounce для предотвращения слишком частых обновлений
		if (this.tabUpdateTimeout) {
			clearTimeout(this.tabUpdateTimeout)
		}

		this.tabUpdateTimeout = setTimeout(() => {
			// Проверяем, работаем ли мы в офлайн-режиме или есть ли подключение
			if (this.isOfflineMode) {
				console.log(
					'Работа в автономном режиме, обновления табулатуры сохраняются только локально'
				)
			} else if (this.socket && this.socket.readyState === WebSocket.OPEN) {
				// Если есть подключение - отправляем данные
				const message = {
					type: 'tab_update',
					tab_text: tabText,
					midi_id: midiId || this.midiId,
				}

				this.socket.send(JSON.stringify(message))
				console.log('Отправлено обновление табулатуры через WebSocket')
			} else {
				console.warn(
					'WebSocket не подключен, обновление табулатуры через WebSocket невозможно'
				)
			}
		}, 300) // Задержка 300 мс
	}

	/**
	 * Регистрирует callback для обновления табулатуры
	 */
	onTabUpdate(callback) {
		if (typeof callback === 'function') {
			this.onTabUpdateCallbacks.push(callback)
		}
	}

	/**
	 * Уведомляет все зарегистрированные callbacks об обновлении
	 */
	notifyTabUpdateCallbacks(tabText, midiId) {
		this.onTabUpdateCallbacks.forEach(callback => {
			try {
				callback(tabText, midiId)
			} catch (e) {
				console.error('Ошибка в callback обновления табулатуры:', e)
			}
		})
	}

	/**
	 * Закрывает соединение
	 */
	disconnect() {
		this.stopPingInterval()

		if (this.socket) {
			this.socket.close()
			this.socket = null
		}
	}
}

// Экспортируем синглтон для использования в других модулях
window.tabWebSocket = new TabWebSocket()

/**
 * Инициализация WebSocket для табулатуры при загрузке страницы
 */
document.addEventListener('DOMContentLoaded', function () {
	// Находим элементы табулатуры на странице
	const tabRows = document.querySelectorAll('.track-row[data-midi-id]')
	if (tabRows.length > 0) {
		// Берем первый MIDI ID для подключения
		const midiId = tabRows[0].getAttribute('data-midi-id')
		// Получаем project_id из URL
		const projectId = window.location.pathname.split('/')[2]

		// Подключаемся к WebSocket
		if (midiId && projectId) {
			window.tabWebSocket.connect(projectId, midiId)
		}
	}

	// Добавляем стили для индикатора соединения
	const style = document.createElement('style')
	style.textContent = `
        .connection-status {
            position: absolute;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 1000;
            background: rgba(0, 0, 0, 0.6);
            color: white;
        }
        .status-connected i {
            color: #4CAF50;
        }
        .status-disconnected i {
            color: #FFC107;
        }
        .status-failed i {
            color: #F44336;
        }
    `
	document.head.appendChild(style)
})

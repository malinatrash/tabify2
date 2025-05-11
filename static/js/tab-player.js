/**
 * Tab Player - скрипт для одновременного воспроизведения всех табулатур в проекте
 * с учетом темпа и синхронизацией между дорожками
 */

class TabPlayer {
	constructor() {
		console.log('[TabPlayer] Инициализация табулатурного плеера')
		
		// Определяем доступные инструменты
		this.instruments = {
			'guitar': {
				name: 'Гитара',
				synth: options => new Tone.PolySynth(Tone.Synth, {
					envelope: {
						attack: 0.005,
						decay: 0.1,
						sustain: 0.3,
						release: 1.5
					},
					oscillator: {
						type: 'fmsine',
						modulationType: 'sine'
					}
				}),
				effects: [
					() => new Tone.Distortion(0.2),
					() => new Tone.Reverb(0.5)
				]
			},
			'piano': {
				name: 'Фортепиано',
				synth: options => new Tone.PolySynth(Tone.Synth, {
					envelope: {
						attack: 0.01,
						decay: 0.5,
						sustain: 0.4,
						release: 2
					},
					oscillator: {
						type: 'triangle'
					}
				}),
				effects: [
					() => new Tone.Reverb(0.8)
				]
			},
			'synth': {
				name: 'Синтезатор',
				synth: options => new Tone.PolySynth(Tone.Synth, {
					envelope: {
						attack: 0.02,
						decay: 0.2,
						sustain: 0.5,
						release: 1
					},
					oscillator: {
						type: 'sawtooth'
					}
				}),
				effects: [
					() => new Tone.Chorus(4, 2.5, 0.5),
					() => new Tone.PingPongDelay("8n", 0.2)
				]
			}
		};

		// Используемый инструмент - по умолчанию гитара
		this.currentInstrument = 'guitar';
		
		// Темп проекта (BPM)
		this.tempo = parseInt(
			document.getElementById('project-tempo-value')?.textContent || '120'
		)
		console.log(`[TabPlayer] Темп проекта: ${this.tempo} BPM`)

		// Флаги инициализации и воспроизведения
		this.audioInitialized = false
		this.isPlaying = false

		// Текущая позиция воспроизведения
		this.currentPosition = 0

		// Контейнер для всех табулатур
		this.tabsContainer = document.querySelector('#tracks-display')
		console.log(`[TabPlayer] Найдены табулатуры: ${this.tabsContainer ? 'да' : 'нет'}`)

		// Все табулатуры в проекте
		// Ищем табулатуры в правильном расположении DOM
		this.tabs = Array.from(document.querySelectorAll('.tab-notation'))
		if (this.tabs.length === 0) {
			// Пробуем найти табулатуры в .tablature-content
			const tabContentElements = document.querySelectorAll('.tablature-content')
			console.log(`[TabPlayer] Найдено контейнеров табулатур: ${tabContentElements.length}`)
			
			// Если есть контейнеры, но нет отрендеренных табулатур, попробуем получить текст напрямую
			tabContentElements.forEach(element => {
				const tabText = element.getAttribute('data-tab-text')
				if (tabText) {
					console.log(`[TabPlayer] Найден текст табулатуры длиной: ${tabText.length} символов`)
					
					// Создаем виртуальный элемент табулатуры для проигрывания
					const virtualTab = document.createElement('pre')
					virtualTab.className = 'virtual-tab'
					virtualTab.textContent = tabText
					virtualTab.setAttribute('data-midi-id', element.closest('.track-row')?.getAttribute('data-midi-id') || '')
					
					// Добавляем в массив табулатур
					this.tabs.push(virtualTab)
				}
			})
		}
		
		console.log(`[TabPlayer] Найдено табулатур: ${this.tabs.length}`)

		// Карта звуков (будет заполнена при инициализации)
		this.sounds = {}

		// Создаем визуальный курсор для отслеживания проигрывания
		this.createPlaybackCursor()

		// Добавляем элементы управления в интерфейс
		this.addPlaybackControls()
	}

	/**
	 * Инициализирует звуки для гитарных струн
	 */
	async initSounds() {
		// Если Tone.js не загружен, выводим предупреждение в консоль
		if (!window.Tone) {
			console.warn('Библиотека Tone.js не загружена, звуки будут генерироваться базовым способом')
		}

		// Названия струн и их ноты в стандартном строе
		const strings = [
			{ name: 'E', note: 'E2', freq: 82.41 },
			{ name: 'A', note: 'A2', freq: 110.0 },
			{ name: 'D', note: 'D3', freq: 146.83 },
			{ name: 'G', note: 'G3', freq: 196.0 },
			{ name: 'B', note: 'B3', freq: 246.94 },
			{ name: 'e', note: 'E4', freq: 329.63 },
		]

		// Определяем доступные инструменты
		this.instruments = {
			'guitar': {
				name: 'Гитара',
				synth: options => new Tone.PolySynth(Tone.Synth, {
					envelope: {
						attack: 0.005,
						decay: 0.1,
						sustain: 0.3,
						release: 1.5
					},
					oscillator: {
						type: 'fmsine',
						modulationType: 'sine'
					}
				}),
				effects: [
					() => new Tone.Distortion(0.2),
					() => new Tone.Reverb(0.5)
				]
			},
			'piano': {
				name: 'Фортепиано',
				synth: options => new Tone.PolySynth(Tone.Synth, {
					envelope: {
						attack: 0.01,
						decay: 0.5,
						sustain: 0.4,
						release: 2
					},
					oscillator: {
						type: 'triangle'
					}
				}),
				effects: [
					() => new Tone.Reverb(0.8)
				]
			},
			'synth': {
				name: 'Синтезатор',
				synth: options => new Tone.PolySynth(Tone.Synth, {
					envelope: {
						attack: 0.02,
						decay: 0.2,
						sustain: 0.5,
						release: 1
					},
					oscillator: {
						type: 'sawtooth'
					}
				}),
				effects: [
					() => new Tone.Chorus(4, 2.5, 0.5),
					() => new Tone.PingPongDelay("8n", 0.2)
				]
			}
		};

		// Используемый инструмент - по умолчанию гитара
		this.currentInstrument = 'guitar';

		// Инициализируем Tone.js
		try {
			await Tone.start();
			// Настраиваем мастер-громкость (используем современный API)
			Tone.getDestination().volume.value = -10;
			console.log('Tone.js успешно инициализирован');
		} catch (error) {
			console.error('Ошибка инициализации Tone.js:', error);
		}

		// Создаем синтезатор для выбранного инструмента
		const createInstrument = (instrumentType) => {
			const instrument = this.instruments[instrumentType];
			if (!instrument) {
				console.error(`Инструмент ${instrumentType} не найден`);
				return null;
			}

			// Создаем синтезатор
			const synth = instrument.synth().toDestination();
			
			// Добавляем эффекты
			const effects = [];
			instrument.effects.forEach(effectFn => {
				const effect = effectFn().toDestination();
				synth.connect(effect);
				effects.push(effect);
			});

			return { synth, effects };
		};

		// Создаем для каждой струны свой синтезатор
		for (const string of strings) {
			try {
				// Создаем инструмент
				const instrument = createInstrument(this.currentInstrument);
				if (!instrument) continue;

				// Создаем функцию для воспроизведения ноты
				this.sounds[string.name] = {
					baseFrequency: string.freq,
					instrument: instrument,
					play: (fret, duration = '8n') => { // по умолчанию 1/8 нота
						// Вычисляем ноту на основе лада
						const note = Tone.Frequency(string.note).transpose(fret).toNote();
						const now = Tone.now();
						
						// Добавляем велосити в зависимости от лада
						const velocity = Math.max(0.5, 1 - (fret * 0.02));
						
						// Воспроизводим ноту с указанной длительностью
						try {
							instrument.synth.triggerAttackRelease(note, duration, now, velocity);
							console.log(`Играем ноту ${note} на струне ${string.name}, лад ${fret}, длительность ${duration}`);
						} catch (error) {
							console.error('Ошибка воспроизведения ноты:', error);
						}
					}
				}

				console.log(`Инициализирован синтезатор для струны ${string.name} (${string.note})`)
				
			} catch (error) {
				console.error(`Ошибка инициализации звука для струны ${string.name}:`, error)
				
				// Резервный вариант - базовый синтезатор
				this.sounds[string.name] = {
					baseFrequency: string.freq,
					play: (fret) => {
						const oscillator = this.audioContext.createOscillator()
						oscillator.type = 'triangle'
						const frequency = string.freq * Math.pow(2, fret/12)
						oscillator.frequency.value = frequency
						
						const gainNode = this.audioContext.createGain()
						gainNode.gain.setValueAtTime(0.3, this.audioContext.currentTime)
						gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 1)
						
						oscillator.connect(gainNode)
						gainNode.connect(this.audioContext.destination)
						
						oscillator.start()
						oscillator.stop(this.audioContext.currentTime + 1)
					}
				}
			}
		}
	}

	/**
	 * Парсит текст табулатуры и извлекает ноты с их временными позициями
	 */
	parseTab(tabText) {
		if (!tabText) {
			console.warn('Пустой текст табулатуры');
			return { strings: {}, length: 0, measures: [] };
		}
		
		// Разбиваем на строки и удаляем пустые строки
		const lines = tabText.split('\n').filter(line => line.trim().length > 0);
		
		if (lines.length === 0) {
			console.warn('Нет строк табулатуры');
			return { strings: {}, length: 0, measures: [] };
		}
		
		const tabData = {
			strings: {},
			length: 0,
			measures: [] // Информация о тактах
		};

		// Базовые настройки для тактов
		const timeSignature = { beats: 4, value: 4 }; // Размер такта 4/4 по умолчанию
		const eightNotesPerBeat = 2; // Сколько восьмых в одной четверти
		
		// Вычисляем количество символов в одном такте
		const symbolsPerMeasure = timeSignature.beats * eightNotesPerBeat;

		// Находим строки табулатуры, определяя строки гитары по шаблону
		const stringIdentifiers = ['e', 'B', 'G', 'D', 'A', 'E'];
		const tabLines = [];
		
		// Пытаемся определить формат табулатуры
		let lineFormat = null;
		
		// Проверяем каждую строку для идентификации формата
		for (const line of lines) {
			// Формат: e|---0---1---|  или  e|-0-1-|
			if (line.match(/^[eEBGDAa]\|[-0-9~phbrvsx\/\\\.].*\|$/)) {
				lineFormat = 'standard';
				break;
			}
			// Формат: E |---0---1---| или E: ---0---1---
			else if (line.match(/^[eEBGDAa]\s*[\|:][-0-9~phbrvsx\/\\\.].*/) || 
					 line.match(/^[eEBGDAa]:\s*[-0-9~phbrvsx\/\\\.].*$/)) {
				lineFormat = 'alternative';
				break;
			}
		}

		if (!lineFormat) {
			// Если формат не определен, пробуем найти строки, которые выглядят как табулатура
			for (const line of lines) {
				// Любая строка, которая содержит много дефисов и некоторые цифры
				if (line.match(/[-0-9]{10,}/)) {
					lineFormat = 'unstructured';
					break;
				}
			}
		}

		if (!lineFormat) {
			console.warn('Не удалось определить формат табулатуры');
			return { strings: {}, length: 0, measures: [] };
		}

		// Находим строки табулатуры на основе определенного формата
		lines.forEach(line => {
			let stringName = null;
			let content = null;

			if (lineFormat === 'standard') {
				// Проверяем стандартный формат: e|---0---1---|
				for (const id of stringIdentifiers) {
					if (line.startsWith(id + '|')) {
						stringName = id;
						// Извлекаем содержимое между | и |
						const matches = line.match(/^[eEBGDAa]\|(.*?)\|$/);
						if (matches && matches[1]) {
							content = matches[1];
						}
						break;
					}
				}
			} else if (lineFormat === 'alternative') {
				// Проверяем альтернативные форматы
				for (const id of stringIdentifiers) {
					// Формат: E |---0---1---|
					if (line.match(new RegExp(`^${id}\s*\|`))) {
						stringName = id;
						const matches = line.match(/^[eEBGDAa]\s*\|(.*?)(?:\||$)/);
						if (matches && matches[1]) {
							content = matches[1];
						}
						break;
					}
					// Формат: E: ---0---1---
					else if (line.match(new RegExp(`^${id}:`))) {
						stringName = id;
						const matches = line.match(/^[eEBGDAa]:\s*(.*)$/);
						if (matches && matches[1]) {
							content = matches[1];
						}
						break;
					}
				}
			} else if (lineFormat === 'unstructured' && line.match(/[-0-9]{10,}/)) {
				// Для неструктурированного формата присваиваем струны в порядке появления
				// Определяем, какую струну назначить этой строке
				const existingStrings = Object.keys(tabData.strings);
				const unusedStrings = stringIdentifiers.filter(s => !existingStrings.includes(s));
				
				if (unusedStrings.length > 0) {
					stringName = unusedStrings[0];
					content = line.trim();
				}
			}

			if (stringName && content) {
				// Нормализуем содержимое, удаляем нетабовые символы
				const cleanContent = content.replace(/[^0-9\-~phbrvsx\/\\]/g, '-');
				
				tabData.strings[stringName] = { content: cleanContent, notes: [] };
				tabData.length = Math.max(tabData.length, cleanContent.length);

				// Находим все ноты в строке
				for (let i = 0; i < cleanContent.length; i++) {
					const char = cleanContent[i];
					
					// Вычисляем номер такта и позицию
					const measureIndex = Math.floor(i / symbolsPerMeasure);
					const beatPosition = i % symbolsPerMeasure;
					
					// Базовая длительность - восьмая нота
					const duration = '8n';
					
					// Добавляем информацию о такте
					if (!tabData.measures[measureIndex]) {
						tabData.measures[measureIndex] = {
							index: measureIndex,
							start: measureIndex * symbolsPerMeasure,
							end: (measureIndex + 1) * symbolsPerMeasure - 1
						};
					}
					
					// Извлекаем ноты
					if (/[0-9]/.test(char)) {
						// Проверка на двузначные числа (10-24)
						if (i + 1 < cleanContent.length && /[0-9]/.test(cleanContent[i + 1])) {
							const fret = parseInt(char + cleanContent[i + 1]);
							tabData.strings[stringName].notes.push({ 
								position: i, 
								fret,
								stringName,
								measure: measureIndex,
								beatPosition,
								duration
							});
							i++; // Пропускаем следующую цифру
						} else {
							// Одиночные цифры (0-9)
							const fret = parseInt(char);
							tabData.strings[stringName].notes.push({ 
								position: i, 
								fret,
								stringName,
								measure: measureIndex,
								beatPosition,
								duration
							});
						}
					}
				}
			}
		});

		// Отладочная информация
		console.log(`Распознано ${Object.keys(tabData.strings).length} струн табулатуры:`, 
			Object.keys(tabData.strings).map(key => `${key}: ${tabData.strings[key].notes.length} нот`).join(', '));

		return tabData;
	}

	/**
	 * Создает визуальный курсор для отслеживания воспроизведения
	 */
	createPlaybackCursor() {
		this.cursor = document.createElement('div')
		this.cursor.className = 'playback-cursor'
		this.cursor.style.cssText = `
            position: absolute;
            top: 0;
            height: 100%;
            width: 2px;
            background-color: #ff6b6b;
            z-index: 10;
            display: none;
            pointer-events: none;
            transition: left 0.1s linear;
        `

		// Добавляем курсор к контейнеру табулатур
		if (this.tabsContainer) {
			this.tabsContainer.style.position = 'relative'
			this.tabsContainer.appendChild(this.cursor)
		}
	}

	/**
	 * Добавляет элементы управления воспроизведением
	 */
	addPlaybackControls() {
		// Создаем контейнер для контролов воспроизведения
		const controlsContainer = document.createElement('div')
		controlsContainer.className = 'player-controls'
		controlsContainer.style.cssText = `
            display: flex;
            align-items: center;
            gap: 10px;
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
            background-color: rgba(40, 44, 52, 0.8);
            backdrop-filter: blur(8px);
            padding: 8px 12px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
        `

		// Создаем выпадающий список для выбора инструмента
		const instrumentSelect = document.createElement('select')
		instrumentSelect.className = 'instrument-select'
		instrumentSelect.style.cssText = `
            background-color: rgba(255, 255, 255, 0.1);
            color: white;
            border: none;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 0.85rem;
            cursor: pointer;
            outline: none;
        `

		// Добавляем доступные инструменты
		Object.keys(this.instruments).forEach(key => {
			const option = document.createElement('option')
			option.value = key
			option.textContent = this.instruments[key].name
			if (key === this.currentInstrument) {
				option.selected = true
			}
			instrumentSelect.appendChild(option)
		})

		// Обработчик изменения инструмента
		instrumentSelect.addEventListener('change', (e) => {
			this.currentInstrument = e.target.value
			// Если уже инициализированы звуки, переинициализируем
			if (this.audioInitialized) {
				// Останавливаем воспроизведение, если оно идет
				if (this.isPlaying) {
					this.stop()
				}
				// Переинициализируем звуки
				this.audioInitialized = false
			}
		})

		// Создаем кнопку Play
		const playButton = document.createElement('button')
		playButton.className = 'vision-btn'
		playButton.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            padding: 8px 16px;
            border-radius: 8px;
            transition: all 0.2s ease;
            color: white;
            background-color: var(--accent-color, #ff6b6b); /* Используем основной акцентный цвет из дизайна */
            border: none;
            cursor: pointer;
        `
		playButton.innerHTML = '<i class="fas fa-play"></i> Play'
		playButton.onclick = () => this.togglePlay()

		// Добавляем элементы в контейнер
		controlsContainer.appendChild(instrumentSelect)
		controlsContainer.appendChild(playButton)
		
		// Добавляем контейнер в body
		document.body.appendChild(controlsContainer)

		// Сохраняем ссылки на элементы управления
		this.controls = {
			container: controlsContainer,
			playButton: playButton,
			instrumentSelect: instrumentSelect
		}
	}

	/**
	 * Запускает или останавливает воспроизведение
	 */
	togglePlay() {
		if (this.isPlaying) {
			this.stop()
		} else {
			this.play()
		}
	}

	/**
	 * Начинает воспроизведение всех табулатур
	 */
	async play() {
		if (this.isPlaying) return
		
		try {
			// Инициализируем звуки при первом нажатии
			if (!this.audioInitialized) {
				// Отобразим сообщение о загрузке
				this.controls.playButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Загрузка...';
				
				// Создаем AudioContext при первом взаимодействии пользователя
				this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
				
				// Инициализируем звуки
				await this.initSounds();
				this.audioInitialized = true;
			}
			
			// Активируем аудио контекст (если он был приостановлен)
			if (this.audioContext.state === 'suspended') {
				await this.audioContext.resume();
			}

			// Обновляем UI
			this.isPlaying = true;
			this.controls.playButton.innerHTML = '<i class="fas fa-stop"></i> Stop';
			this.cursor.style.display = 'block';
			this.cursor.style.left = '0px';

			// Парсим все табулатуры
			this.parsedTabs = [];
			this.tabs.forEach(tabElement => {
				const tabText = tabElement.textContent;
				const tabData = this.parseTab(tabText);
				this.parsedTabs.push(tabData);
			});
		} catch (error) {
			console.error('Ошибка при инициализации звука:', error);
			this.controls.playButton.innerHTML = '<i class="fas fa-play"></i> Play';
			alert('Не удалось запустить воспроизведение. Попробуйте еще раз.');
			return;
		}

		// Находим максимальную длину всех табулатур
		const maxLength = Math.max(...this.parsedTabs.map(tab => tab.length))

		// Вычисляем длительность одного символа табулатуры в миллисекундах
		const symbolDuration = 60000 / this.tempo / 4 // 1/4 ноты (предполагаем 4/4 такт)

		// Запускаем воспроизведение
		this.startTime = this.audioContext.currentTime
		this.currentPosition = 0

		// Создаем план воспроизведения
		this.schedule = []

		// Формируем план воспроизведения для всех нот из всех табулатур, учитывая длительности
		this.parsedTabs.forEach(tab => {
			Object.entries(tab.strings).forEach(([stringName, data]) => {
				data.notes.forEach(note => {
					// Используем информацию о позиции в такте и длительности (1/8 нота)
					this.schedule.push({
						time: note.position * symbolDuration,  // Позиция в символах * длительность символа
						string: stringName,
						fret: note.fret,
						duration: note.duration || '8n',  // Используем длительность, если есть, или по умолчанию 1/8
						measure: note.measure || 0,  // Номер такта
						beatPosition: note.beatPosition || 0  // Позиция в такте
					})
				})
			})
		})

		// Сортируем план по времени
		this.schedule.sort((a, b) => a.time - b.time)

		// Запускаем обновление позиции и воспроизведение
		this.updatePlaybackPosition()

		// Добавляем ограничение по времени (предотвращаем бесконечное воспроизведение)
		this.totalDuration = maxLength * symbolDuration
		this.playbackTimeout = setTimeout(() => {
			this.stop()
		}, this.totalDuration)
	}

	/**
	 * Останавливает воспроизведение
	 */
	stop() {
		if (!this.isPlaying) return

		// Обновляем UI
		this.isPlaying = false
		this.controls.playButton.innerHTML = '<i class="fas fa-play"></i> Play'
		this.cursor.style.display = 'none'

		// Останавливаем все таймеры
		clearTimeout(this.playbackTimeout)
		cancelAnimationFrame(this.animationFrame)
	}

	/**
	 * Обновляет позицию курсора и воспроизводит необходимые ноты
	 */
	updatePlaybackPosition() {
		// Вычисляем текущее положение
		const elapsedTime = this.audioContext.currentTime - this.startTime
		const symbolDuration = 60000 / this.tempo / 4 // 1/4 ноты

		// Обновляем позицию курсора
		if (this.tabsContainer) {
			const containerWidth = this.tabsContainer.clientWidth
			const relativePosition = Math.min(
				1,
				(elapsedTime * 1000) / this.totalDuration
			)
			this.cursor.style.left = `${relativePosition * containerWidth}px`
		}

		// Проигрываем все ноты, которые должны прозвучать в текущий момент
		this.schedule.forEach((note, index) => {
			if (!note.played && elapsedTime * 1000 >= note.time) {
				// Воспроизводим ноту с указанной длительностью
				if (this.sounds[note.string]) {
					// Используем длительность из ноты (1/8 по умолчанию)
					this.sounds[note.string].play(note.fret, note.duration || '8n')
					console.log(`Проигрываем ноту на струне ${note.string}, лад ${note.fret}, такт ${note.measure}, позиция ${note.beatPosition}, длительность ${note.duration || '8n'}`)
				}
				// Отмечаем ноту как воспроизведенную
				this.schedule[index].played = true
			}
		})

		// Продолжаем обновление, если все еще воспроизводим
		if (this.isPlaying) {
			this.animationFrame = requestAnimationFrame(() =>
				this.updatePlaybackPosition()
			)
		}
	}
}

// Инициализация плеера при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
	// Небольшая задержка для уверенности, что все DOM элементы загружены
	setTimeout(() => {
		window.tabPlayer = new TabPlayer()
	}, 500)
})

/**
 * Sequencer functionality for MIDI tracks and tablature display
 * Упрощенная версия без функций зума и скроллинга
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeSequencer();
    setupFilters();
    setupTrackHandles();
});

/**
 * Initialize the sequencer interface
 */
function initializeSequencer() {
    console.log('Initializing sequencer interface');
    
    // Initialize all track tablatures
    const tablatureElements = document.querySelectorAll('.tablature-content');
    
    tablatureElements.forEach(element => {
        if (element && element.getAttribute('data-tab-text')) {
            try {
                const tabText = element.getAttribute('data-tab-text');
                const midiId = element.closest('.track-row')?.getAttribute('data-midi-id');
                const tabHTML = renderTabFromText(tabText, midiId);
                element.innerHTML = tabHTML;
            } catch (error) {
                console.error('Error rendering tablature:', error);
                element.innerHTML = '<p class="text-danger">Error rendering tablature</p>';
            }
        }
    });
    
    console.log('Sequencer initialized successfully');
}

/**
 * Setup track handles functionality
 */
function setupTrackHandles() {
    const trackRows = document.querySelectorAll('.track-row');
    
    trackRows.forEach(row => {
        const trackHandle = row.querySelector('.track-handle');
        
        if (trackHandle) {
            // Add visual indicator to handle
            const indicator = document.createElement('div');
            indicator.className = 'track-indicator';
            trackHandle.appendChild(indicator);
            
            // Setup hover effects
            row.addEventListener('mouseenter', function() {
                this.classList.add('hover');
            });
            
            row.addEventListener('mouseleave', function() {
                this.classList.remove('hover');
            });
            
            // Setup handle click to toggle track selection
            trackHandle.addEventListener('click', function() {
                row.classList.toggle('selected');
            });
        }
    });
}

/**
 * Setup filter controls
 */
function setupFilters() {
    // Pitch filter range
    const pitchMin = document.getElementById('pitch-min');
    const pitchMax = document.getElementById('pitch-max');
    const pitchMinValue = document.getElementById('pitch-min-value');
    const pitchMaxValue = document.getElementById('pitch-max-value');
    
    // Duration filter range
    const durationMin = document.getElementById('duration-min');
    const durationMax = document.getElementById('duration-max');
    const durationMinValue = document.getElementById('duration-min-value');
    const durationMaxValue = document.getElementById('duration-max-value');
    
    // Initialize range sliders
    if (pitchMin && pitchMax && pitchMinValue && pitchMaxValue) {
        pitchMin.addEventListener('input', function() {
            pitchMinValue.textContent = this.value;
            if (parseInt(this.value) > parseInt(pitchMax.value)) {
                pitchMax.value = this.value;
                pitchMaxValue.textContent = this.value;
            }
            applyFilters();
        });
        
        pitchMax.addEventListener('input', function() {
            pitchMaxValue.textContent = this.value;
            if (parseInt(this.value) < parseInt(pitchMin.value)) {
                pitchMin.value = this.value;
                pitchMinValue.textContent = this.value;
            }
            applyFilters();
        });
    }
    
    if (durationMin && durationMax && durationMinValue && durationMaxValue) {
        durationMin.addEventListener('input', function() {
            durationMinValue.textContent = this.value;
            if (parseInt(this.value) > parseInt(durationMax.value)) {
                durationMax.value = this.value;
                durationMaxValue.textContent = this.value;
            }
            applyFilters();
        });
        
        durationMax.addEventListener('input', function() {
            durationMaxValue.textContent = this.value;
            if (parseInt(this.value) < parseInt(durationMin.value)) {
                durationMin.value = this.value;
                durationMinValue.textContent = this.value;
            }
            applyFilters();
        });
    }
}

/**
 * Apply current filter settings
 */
function applyFilters() {
    const filters = {
        pitch: {
            min: parseInt(document.getElementById('pitch-min')?.value || 0),
            max: parseInt(document.getElementById('pitch-max')?.value || 127)
        },
        duration: {
            min: parseInt(document.getElementById('duration-min')?.value || 0),
            max: parseInt(document.getElementById('duration-max')?.value || 2000)
        }
    };
    
    console.log('Applying filters:', filters);
}

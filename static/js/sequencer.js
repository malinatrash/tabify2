/**
 * Sequencer functionality for MIDI tracks and tablature display
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeSequencer();
    setupFilters();
    setupTrackHandles();
    setupZoomControls();
    setupTimelineScale();
    setupSynchronizedScrolling();
});

/**
 * Setup synchronized scrolling between tracks list and tablatures
 */
function setupSynchronizedScrolling() {
    const tracksDisplay = document.getElementById('tracks-display');
    const tracksList = document.querySelector('.tracks-list');
    
    if (tracksDisplay && tracksList) {
        // Synchronize tracks-display scrolling to tracks-list
        tracksDisplay.addEventListener('scroll', function() {
            // Calculate scroll percentage
            const scrollPercentage = this.scrollTop / (this.scrollHeight - this.clientHeight);
            
            // Apply same scroll percentage to tracks-list
            const tracksListScrollMax = tracksList.scrollHeight - tracksList.clientHeight;
            tracksList.scrollTop = scrollPercentage * tracksListScrollMax;
        });
        
        // Synchronize tracks-list scrolling to tracks-display
        tracksList.addEventListener('scroll', function() {
            // Calculate scroll percentage
            const scrollPercentage = this.scrollTop / (this.scrollHeight - this.clientHeight);
            
            // Apply same scroll percentage to tracks-display
            const tracksDisplayScrollMax = tracksDisplay.scrollHeight - tracksDisplay.clientHeight;
            tracksDisplay.scrollTop = scrollPercentage * tracksDisplayScrollMax;
        });
    }
}

/**
 * Initialize the sequencer interface
 */
function initializeSequencer() {
    console.log('Initializing sequencer interface');
    
    // Initialize all track tablatures
    const tablatureElements = document.querySelectorAll('.tablature-content');
    
    tablatureElements.forEach(element => {
        if (element && element.getAttribute('data-tab-data')) {
            try {
                const tabData = JSON.parse(element.getAttribute('data-tab-data'));
                const tabHTML = renderTabFromJSON(tabData);
                element.innerHTML = tabHTML;
            } catch (error) {
                console.error('Error rendering tablature:', error);
                element.innerHTML = '<p class="text-danger">Error rendering tablature</p>';
            }
        }
    });
    
    // No additional setup needed
    
    // Initialize sequencer is ready
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
 * Setup timeline scale markers
 */
function setupTimelineScale() {
    const timelineScale = document.querySelector('.timeline-scale');
    if (!timelineScale) return;
    
    // Create time markers (each marker is 1 second)
    const totalSeconds = 60; // 1 minute total by default
    
    for (let i = 0; i <= totalSeconds; i += 5) { // Every 5 seconds add a marker
        const marker = document.createElement('div');
        marker.className = 'time-marker';
        marker.style.left = `${(i/totalSeconds) * 100}%`;
        
        const label = document.createElement('span');
        label.className = 'time-label';
        label.textContent = formatTimeLabel(i);
        marker.appendChild(label);
        
        timelineScale.appendChild(marker);
    }
}

/**
 * Format seconds to mm:ss format
 * @param {number} seconds - Total seconds
 * @returns {string} Formatted time string
 */
function formatTimeLabel(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Setup events for tracks navigation
 * @param {HTMLElement} tracksDisplay - The tracks display element
 */
function setupTracksNavigationEvents(tracksDisplay) {
    if (!tracksDisplay) return;
    
    // Handle horizontal scrolling and update position indicator
    tracksDisplay.addEventListener('scroll', function() {
        updateScrollPositionIndicator();
    });
    
    // Handle wheel event for horizontal scrolling with Shift key
    tracksDisplay.addEventListener('wheel', function(e) {
        if (e.shiftKey) {
            e.preventDefault();
            tracksDisplay.scrollLeft += e.deltaY;
        }
    }, { passive: false });
    
    // Handle Ctrl+wheel for zooming all tablatures
    tracksDisplay.addEventListener('wheel', function(e) {
        if (e.ctrlKey) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.05 : 0.05;
            zoomAllTablatures(delta);
        }
    }, { passive: false });
}



/**
 * Zoom all tablatures in the sequencer
 * @param {number} delta - Zoom delta amount
 */
function zoomAllTablatures(delta) {
    const tabNotations = document.querySelectorAll('.tab-notation');
    
    tabNotations.forEach(tab => {
        let currentScale = parseFloat(tab.dataset.scale || '1');
        
        // Apply zoom with limits
        currentScale = Math.max(0.5, Math.min(2.5, currentScale + delta));
        
        // Update scale and apply transform
        tab.dataset.scale = currentScale.toString();
        tab.style.transform = `scale(${currentScale})`;
    });
    
    // Show feedback for zoom level
    const firstTab = tabNotations[0];
    if (firstTab) {
        showZoomLevel(parseFloat(firstTab.dataset.scale || '1'));
    }
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
    
    // Apply filters button
    const applyFiltersBtn = document.getElementById('apply-filters');
    
    // Update displayed values when sliders change
    if (pitchMin) {
        pitchMin.addEventListener('input', function() {
            pitchMinValue.textContent = this.value;
            // Ensure min doesn't exceed max
            if (parseInt(pitchMin.value) > parseInt(pitchMax.value)) {
                pitchMax.value = pitchMin.value;
                pitchMaxValue.textContent = pitchMax.value;
            }
        });
    }
    
    if (pitchMax) {
        pitchMax.addEventListener('input', function() {
            pitchMaxValue.textContent = this.value;
            // Ensure max doesn't go below min
            if (parseInt(pitchMax.value) < parseInt(pitchMin.value)) {
                pitchMin.value = pitchMax.value;
                pitchMinValue.textContent = pitchMin.value;
            }
        });
    }
    
    if (durationMin) {
        durationMin.addEventListener('input', function() {
            durationMinValue.textContent = this.value;
            // Ensure min doesn't exceed max
            if (parseInt(durationMin.value) > parseInt(durationMax.value)) {
                durationMax.value = durationMin.value;
                durationMaxValue.textContent = durationMax.value;
            }
        });
    }
    
    if (durationMax) {
        durationMax.addEventListener('input', function() {
            durationMaxValue.textContent = this.value;
            // Ensure max doesn't go below min
            if (parseInt(durationMax.value) < parseInt(durationMin.value)) {
                durationMin.value = durationMax.value;
                durationMinValue.textContent = durationMin.value;
            }
        });
    }
    
    // Apply filters when button is clicked
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function() {
            const filters = {
                pitchRange: [parseInt(pitchMin.value), parseInt(pitchMax.value)],
                durationRange: [parseInt(durationMin.value), parseInt(durationMax.value)]
            };
            
            applyNotesFilters(filters);
        });
    }
}

/**
 * Apply filters to the notes in the tablature
 * @param {Object} filters - The filter settings
 */
function applyNotesFilters(filters) {
    console.log('Applying filters:', filters);
    // Filters now applied during initial generation
}

/**
 * Setup zoom controls for the tablature
 */
function setupZoomControls() {
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const resetViewBtn = document.getElementById('reset-view');
    
    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', function() {
            zoomAllTablatures(0.1); // Increase zoom by 10%
        });
    }
    
    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', function() {
            zoomAllTablatures(-0.1); // Decrease zoom by 10%
        });
    }
    
    if (resetViewBtn) {
        resetViewBtn.addEventListener('click', function() {
            resetTabView();
        });
    }
}

/**
 * Reset all tablatures view to default
 */
function resetTabView() {
    const tabNotations = document.querySelectorAll('.tab-notation');
    tabNotations.forEach(tab => {
        tab.dataset.scale = '1';
        tab.style.transform = 'scale(1)';
    });
    
    // Reset scroll position
    const tracksDisplay = document.querySelector('.tracks-display');
    if (tracksDisplay) {
        tracksDisplay.scrollLeft = 0;
        tracksDisplay.scrollTop = 0;
    }
    
    showZoomLevel(1);
}/**
 * Show current zoom level indicator
 * @param {number} level - Current zoom level
 */
function showZoomLevel(level) {
    // Create or get zoom indicator
    let zoomIndicator = document.getElementById('zoom-indicator');
    
    if (!zoomIndicator) {
        zoomIndicator = document.createElement('div');
        zoomIndicator.id = 'zoom-indicator';
        zoomIndicator.className = 'zoom-indicator';
        document.querySelector('.tablature-container').appendChild(zoomIndicator);
    }
    
    // Update and show indicator
    zoomIndicator.textContent = `${Math.round(level * 100)}%`;
    zoomIndicator.classList.add('visible');
    
    // Hide after delay
    clearTimeout(window.zoomTimeout);
    window.zoomTimeout = setTimeout(() => {
        zoomIndicator.classList.remove('visible');
    }, 1500);
}





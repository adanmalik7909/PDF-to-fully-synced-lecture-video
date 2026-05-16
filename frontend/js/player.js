/**
 * Lecture Player - Interactive Presentation Mode
 * Handles section navigation, timer, and keyboard shortcuts
 */

// Global state
let lecture = null;
let currentSectionIndex = 0;
let timerInterval = null;
let timerSeconds = 0;
let timerPaused = false;
let isFullscreen = false;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Load lecture from localStorage
    const lectureData = localStorage.getItem('currentLecture');

    if (!lectureData) {
        alert('No lecture data found. Redirecting...');
        window.close();
        return;
    }

    try {
        lecture = JSON.parse(lectureData);
        initializePlayer();
        setupKeyboardShortcuts();
        showShortcutsHelp();
    } catch (error) {
        console.error('Failed to load lecture:', error);
        alert('Failed to load lecture data');
        window.close();
    }
});

// ============================================
// PLAYER INITIALIZATION
// ============================================

function initializePlayer() {
    // Set lecture title
    document.getElementById('lectureTitle').textContent = lecture.title;
    document.getElementById('totalDuration').textContent = lecture.script.duration_minutes + ' minutes';

    // Generate section dots
    generateSectionDots();

    // Load first section
    loadSection(0);

    // Show shortcuts help for 3 seconds
    setTimeout(() => {
        const help = document.getElementById('shortcutsHelp');
        help.classList.add('show');
        setTimeout(() => help.classList.remove('show'), 5000);
    }, 500);
}

// ============================================
// SECTION NAVIGATION
// ============================================

function loadSection(index) {
    const sections = lecture.script.sections || [];

    if (index < 0 || index >= sections.length) {
        // Show assessment summary
        if (index >= sections.length) {
            showAssessmentSummary();
        }
        return;
    }

    currentSectionIndex = index;
    const section = sections[index];

    // Update section indicator
    document.getElementById('sectionIndicator').textContent =
        `Section ${index + 1} of ${sections.length}`;

    // Update progress bar
    const progress = ((index + 1) / sections.length) * 100;
    document.getElementById('progressBar').style.width = progress + '%';
    document.getElementById('currentSection').textContent = section.title;

    // Update section content
    document.getElementById('sectionNumber').textContent = section.section_number;
    document.getElementById('sectionTitle').textContent = section.title;
    document.getElementById('sectionContent').innerHTML = `<p>${section.content}</p>`;

    // Update key points
    const keyPointsList = document.getElementById('keyPoints');
    keyPointsList.innerHTML = (section.key_points || [])
        .map(point => `<li>${point}</li>`)
        .join('');

    // Update activities
    const activitiesList = document.getElementById('activities');
    activitiesList.innerHTML = (section.activities || [])
        .map(activity => `<li>${activity}</li>`)
        .join('');

    // Update speaker notes
    document.getElementById('speakerNotes').innerHTML = `
        <p><strong>Duration:</strong> ${section.duration_minutes} minutes</p>
        <p><strong>Teaching Tips:</strong> Focus on engaging students with the activities listed. 
        Use the key points as a guide for your presentation.</p>
    `;

    // Update section dots
    updateSectionDots();

    // Update navigation buttons
    document.getElementById('prevBtn').disabled = index === 0;
    document.getElementById('nextBtn').textContent =
        index === sections.length - 1 ? 'Finish →' : 'Next →';

    // Start timer for this section
    startSectionTimer(section.duration_minutes);

    // Scroll to top
    document.getElementById('playerContent').scrollTop = 0;

    // Animate content
    const content = document.getElementById('playerContent');
    content.style.animation = 'none';
    setTimeout(() => {
        content.style.animation = 'fadeIn 0.5s ease';
    }, 10);
}

function nextSection() {
    const sections = lecture.script.sections || [];
    if (currentSectionIndex < sections.length - 1) {
        loadSection(currentSectionIndex + 1);
    } else {
        showAssessmentSummary();
    }
}

function previousSection() {
    if (currentSectionIndex > 0) {
        loadSection(currentSectionIndex - 1);
    }
}

function goToSection(index) {
    loadSection(index);
}

// ============================================
// SECTION DOTS
// ============================================

function generateSectionDots() {
    const sections = lecture.script.sections || [];
    const dotsContainer = document.getElementById('sectionDots');

    dotsContainer.innerHTML = sections.map((_, index) =>
        `<div class="dot" onclick="goToSection(${index})" title="Section ${index + 1}"></div>`
    ).join('');
}

function updateSectionDots() {
    const dots = document.querySelectorAll('.dot');
    dots.forEach((dot, index) => {
        if (index === currentSectionIndex) {
            dot.classList.add('active');
        } else {
            dot.classList.remove('active');
        }
    });
}

// ============================================
// TIMER
// ============================================

function startSectionTimer(minutes) {
    // Clear existing timer
    if (timerInterval) {
        clearInterval(timerInterval);
    }

    timerSeconds = minutes * 60;
    timerPaused = false;
    updateTimerDisplay();

    // Start countdown
    timerInterval = setInterval(() => {
        if (!timerPaused && timerSeconds > 0) {
            timerSeconds--;
            updateTimerDisplay();
            updateTimerProgress();

            // Alert when time is up
            if (timerSeconds === 0) {
                clearInterval(timerInterval);
                playTimerAlert();
            }
        }
    }, 1000);
}

function updateTimerDisplay() {
    const minutes = Math.floor(timerSeconds / 60);
    const seconds = timerSeconds % 60;
    const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;

    document.getElementById('timerText').textContent = timeString;
    document.getElementById('timeRemaining').textContent = timeString;
}

function updateTimerProgress() {
    const sections = lecture.script.sections || [];
    const section = sections[currentSectionIndex];
    const totalSeconds = section.duration_minutes * 60;
    const progress = (timerSeconds / totalSeconds) * 283; // 283 is circumference

    document.getElementById('timerProgress').style.strokeDashoffset = 283 - progress;
}

function toggleTimer() {
    timerPaused = !timerPaused;
    const btn = document.getElementById('timerButton');
    btn.textContent = timerPaused ? '▶ Resume' : '⏸ Pause';
}

function playTimerAlert() {
    // Visual alert
    const timerDisplay = document.getElementById('timerDisplay');
    timerDisplay.style.animation = 'pulse 0.5s ease 3';

    // Could add audio alert here
    console.log('⏰ Time is up for this section!');
}

// ============================================
// FULLSCREEN
// ============================================

function toggleFullscreen() {
    const container = document.getElementById('playerContainer');

    if (!isFullscreen) {
        if (container.requestFullscreen) {
            container.requestFullscreen();
        } else if (container.webkitRequestFullscreen) {
            container.webkitRequestFullscreen();
        } else if (container.msRequestFullscreen) {
            container.msRequestFullscreen();
        }
        isFullscreen = true;
        document.getElementById('fullscreenIcon').textContent = '⛶';
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
        isFullscreen = false;
        document.getElementById('fullscreenIcon').textContent = '⛶';
    }
}

// Listen for fullscreen changes
document.addEventListener('fullscreenchange', () => {
    isFullscreen = !!document.fullscreenElement;
});

// ============================================
// SPEAKER NOTES
// ============================================

function toggleNotes() {
    const notesContent = document.getElementById('notesContent');
    const toggleText = document.getElementById('notesToggleText');

    if (notesContent.style.display === 'none') {
        notesContent.style.display = 'block';
        toggleText.textContent = '📝 Hide Notes';
    } else {
        notesContent.style.display = 'none';
        toggleText.textContent = '📝 Show Notes';
    }
}

// ============================================
// ASSESSMENT SUMMARY
// ============================================

function showAssessmentSummary() {
    const assessment = lecture.script.assessment || {};
    const resources = lecture.script.resources || [];

    const assessmentContent = document.getElementById('assessmentContent');
    const resourcesContent = document.getElementById('resourcesContent');

    assessmentContent.innerHTML = `
        <div style="margin-bottom: 2rem; padding: 1.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 12px;">
            <h3 style="font-size: 1.5rem; margin-bottom: 1rem;">Assessment</h3>
            <p><strong>Type:</strong> ${assessment.type || 'N/A'}</p>
            <p style="margin-top: 0.5rem;"><strong>Description:</strong> ${assessment.description || 'N/A'}</p>
            <div style="margin-top: 1rem;">
                <strong>Rubric:</strong>
                <ul style="margin-top: 0.5rem; margin-left: 1.5rem;">
                    ${(assessment.rubric || []).map(item => `<li>${item}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;

    resourcesContent.innerHTML = `
        <div style="padding: 1.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 12px;">
            <h3 style="font-size: 1.5rem; margin-bottom: 1rem;">Resources</h3>
            <ul style="margin-left: 1.5rem;">
                ${resources.map(resource => `<li>${resource}</li>`).join('')}
            </ul>
        </div>
    `;

    document.getElementById('assessmentSummary').style.display = 'flex';
}

function restartLecture() {
    document.getElementById('assessmentSummary').style.display = 'none';
    loadSection(0);
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        switch (e.key) {
            case 'ArrowRight':
                e.preventDefault();
                nextSection();
                break;
            case 'ArrowLeft':
                e.preventDefault();
                previousSection();
                break;
            case 'f':
            case 'F':
                e.preventDefault();
                toggleFullscreen();
                break;
            case ' ':
                e.preventDefault();
                toggleTimer();
                break;
            case 'n':
            case 'N':
                e.preventDefault();
                toggleNotes();
                break;
            case 'Escape':
                if (isFullscreen) {
                    toggleFullscreen();
                } else {
                    closePlaye();
                }
                break;
            case '?':
                showShortcutsHelp();
                break;
        }
    });
}

function showShortcutsHelp() {
    const help = document.getElementById('shortcutsHelp');
    help.classList.add('show');
}

function closeShortcutsHelp() {
    const help = document.getElementById('shortcutsHelp');
    help.classList.remove('show');
}

// ============================================
// UTILITIES
// ============================================

function closePlaye() {
    if (confirm('Are you sure you want to exit the lecture player?')) {
        if (timerInterval) {
            clearInterval(timerInterval);
        }
        window.close();
        // If window.close() doesn't work (some browsers block it)
        window.location.href = 'teacher_lectures.html';
    }
}

// Add pulse animation dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }
`;
document.head.appendChild(style);

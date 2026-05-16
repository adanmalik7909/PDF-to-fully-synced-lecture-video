/**
 * Lecture Generation Module - Main JavaScript
 * Handles PDF upload, lecture generation, and UI interactions
 */

// Global state
let currentUser = null;
let documents = [];
let lectures = [];
let currentLecture = null;

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    // Check authentication
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    // Get user info
    try {
        currentUser = await API.getCurrentUser();
        document.getElementById('userName').textContent = currentUser.username;
    } catch (error) {
        console.error('Failed to get user:', error);
        window.location.href = '/login';
        return;
    }

    // Setup event listeners
    setupEventListeners();

    // Load initial data
    await loadDocuments();
    loadLectures();
});

// ============================================
// EVENT LISTENERS
// ============================================

function setupEventListeners() {
    // File upload
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');

    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', loadDocuments);

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', logout);
}

// ============================================
// FILE UPLOAD
// ============================================

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

async function handleFile(file) {
    // Validate file
    if (!file.type.includes('pdf')) {
        showToast('Please upload a PDF file', 'error');
        return;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
        showToast('File size must be less than 10MB', 'error');
        return;
    }

    // Show progress
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    uploadProgress.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = 'Uploading...';

    try {
        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 10;
            if (progress <= 90) {
                progressFill.style.width = progress + '%';
            }
        }, 200);

        // Upload file
        const result = await API.uploadContent(file);

        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = 'Upload complete! Processing...';

        showToast('PDF uploaded successfully! Processing content...', 'success');

        // Wait a bit then reload documents
        setTimeout(async () => {
            uploadProgress.style.display = 'none';
            await loadDocuments();

            // Reset file input
            document.getElementById('fileInput').value = '';
        }, 2000);

    } catch (error) {
        console.error('Upload error:', error);
        uploadProgress.style.display = 'none';
        showToast('Upload failed: ' + error.message, 'error');
    }
}

// ============================================
// LOAD DOCUMENTS
// ============================================

async function loadDocuments() {
    const grid = document.getElementById('documentsGrid');

    try {
        // Show loading
        grid.innerHTML = `
            <div class="loading-skeleton">
                <div class="skeleton-card"></div>
                <div class="skeleton-card"></div>
                <div class="skeleton-card"></div>
            </div>
        `;

        // Fetch documents
        documents = await API.listContents();

        if (documents.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📄</div>
                    <h3>No Documents Yet</h3>
                    <p>Upload your first PDF to get started!</p>
                </div>
            `;
            return;
        }

        // Render documents
        grid.innerHTML = documents.map(doc => createDocumentCard(doc)).join('');

    } catch (error) {
        console.error('Failed to load documents:', error);
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <h3>Failed to Load Documents</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

function createDocumentCard(doc) {
    const statusClass = doc.rag_status === 'completed' ? 'status-completed' :
        doc.rag_status === 'processing' ? 'status-processing' : 'status-pending';

    const statusText = doc.rag_status === 'completed' ? '✓ Ready' :
        doc.rag_status === 'processing' ? '⏳ Processing' : '⏸ Pending';

    const canGenerate = doc.rag_status === 'completed';

    return `
        <div class="document-card">
            <div class="document-header">
                <div class="document-icon">📄</div>
                <div class="document-info">
                    <div class="document-name">${doc.filename}</div>
                    <div class="document-meta">
                        ${formatFileSize(doc.file_size)} • ${formatDate(doc.uploaded_at)}
                    </div>
                    <span class="document-status ${statusClass}">${statusText}</span>
                </div>
            </div>
            <div class="document-actions">
                <button class="btn-action btn-generate" 
                        onclick="openGenerateModal(${doc.id}, '${doc.filename}')"
                        ${!canGenerate ? 'disabled' : ''}>
                    🎓 Generate Lecture
                </button>
                <button class="btn-action btn-delete" onclick="deleteDocument(${doc.id})">
                    🗑️ Delete
                </button>
            </div>
        </div>
    `;
}

// ============================================
// GENERATE LECTURE MODAL
// ============================================

function openGenerateModal(contentId, filename) {
    document.getElementById('modalContentId').value = contentId;
    document.getElementById('modalDocumentName').value = filename;
    document.getElementById('lectureTitle').value = '';

    // Reset objectives to 3 default ones
    const container = document.getElementById('objectivesContainer');
    container.innerHTML = `
        <div class="objective-item">
            <input type="text" class="objective-input" placeholder="Objective 1: e.g., Understand core concepts">
            <button class="btn-remove" onclick="removeObjective(this)">✕</button>
        </div>
        <div class="objective-item">
            <input type="text" class="objective-input" placeholder="Objective 2: e.g., Apply techniques practically">
            <button class="btn-remove" onclick="removeObjective(this)">✕</button>
        </div>
        <div class="objective-item">
            <input type="text" class="objective-input" placeholder="Objective 3: e.g., Evaluate different approaches">
            <button class="btn-remove" onclick="removeObjective(this)">✕</button>
        </div>
    `;

    document.getElementById('generateModal').classList.add('active');
}

function closeGenerateModal() {
    document.getElementById('generateModal').classList.remove('active');
}

function addObjective() {
    const container = document.getElementById('objectivesContainer');
    const count = container.children.length;

    if (count >= 10) {
        showToast('Maximum 10 objectives allowed', 'error');
        return;
    }

    const div = document.createElement('div');
    div.className = 'objective-item';
    div.innerHTML = `
        <input type="text" class="objective-input" placeholder="Objective ${count + 1}">
        <button class="btn-remove" onclick="removeObjective(this)">✕</button>
    `;
    container.appendChild(div);
}

function removeObjective(btn) {
    const container = document.getElementById('objectivesContainer');
    if (container.children.length <= 1) {
        showToast('At least one objective is required', 'error');
        return;
    }
    btn.parentElement.remove();
}

// ============================================
// GENERATE LECTURE
// ============================================

async function generateLecture() {
    const contentId = parseInt(document.getElementById('modalContentId').value);
    const title = document.getElementById('lectureTitle').value.trim();

    // Get objectives
    const objectiveInputs = document.querySelectorAll('.objective-input');
    const objectives = Array.from(objectiveInputs)
        .map(input => input.value.trim())
        .filter(obj => obj.length > 0);

    if (objectives.length === 0) {
        showToast('Please enter at least one learning objective', 'error');
        return;
    }

    // Show loading state
    const generateBtn = document.getElementById('generateBtn');
    const btnText = generateBtn.querySelector('.btn-text');
    const btnLoader = generateBtn.querySelector('.btn-loader');

    btnText.style.display = 'none';
    btnLoader.style.display = 'inline';
    generateBtn.disabled = true;

    try {
        // Call API
        const result = await API.generateLecture(contentId, objectives, title);

        // Store lecture
        const lecture = {
            id: Date.now(),
            contentId: contentId,
            title: result.lecture_script.title,
            script: result.lecture_script,
            generatedAt: new Date().toISOString(),
            model: result.model_used
        };

        // Save to localStorage
        lectures.push(lecture);
        saveLectures();

        // Close modal
        closeGenerateModal();

        // Show success
        showToast('Lecture generated successfully!', 'success');

        // Reload lectures
        loadLectures();

        // Open preview
        setTimeout(() => {
            openLecturePreview(lecture);
        }, 500);

    } catch (error) {
        console.error('Generation error:', error);
        showToast('Failed to generate lecture: ' + error.message, 'error');
    } finally {
        // Reset button
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
        generateBtn.disabled = false;
    }
}

// ============================================
// LOAD LECTURES
// ============================================

function loadLectures() {
    // Load from localStorage
    const stored = localStorage.getItem('lectures');
    if (stored) {
        lectures = JSON.parse(stored);
    }

    const grid = document.getElementById('lecturesGrid');
    const emptyState = document.getElementById('emptyState');

    if (lectures.length === 0) {
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';
    grid.innerHTML = lectures.map(lecture => createLectureCard(lecture)).join('');
}

function saveLectures() {
    localStorage.setItem('lectures', JSON.stringify(lectures));
}

function createLectureCard(lecture) {
    const sections = lecture.script.sections || [];
    const duration = lecture.script.duration_minutes || 0;

    return `
        <div class="lecture-card">
            <div class="lecture-title">${lecture.title}</div>
            <div class="lecture-meta">
                <span>⏱️ ${duration} min</span>
                <span>📑 ${sections.length} sections</span>
                <span>🤖 ${lecture.model}</span>
            </div>
            <div class="lecture-sections">
                ${sections.slice(0, 3).map(section => `
                    <div class="section-preview">
                        <h4>${section.section_number}. ${section.title}</h4>
                        <p>${section.duration_minutes} min • ${section.key_points?.length || 0} key points</p>
                    </div>
                `).join('')}
                ${sections.length > 3 ? `<p style="text-align: center; color: #6b7280; font-size: 0.875rem;">+${sections.length - 3} more sections</p>` : ''}
            </div>
            <div class="lecture-actions">
                <button class="btn-action btn-view" onclick='openLecturePreview(${JSON.stringify(lecture).replace(/'/g, "&apos;")})'>
                    👁️ View
                </button>
                <button class="btn-action btn-generate" onclick="openPlayer(${lecture.id})">
                    🎬 Play
                </button>
                <button class="btn-action btn-delete" onclick="deleteLecture(${lecture.id})">
                    🗑️ Delete
                </button>
            </div>
        </div>
    `;
}

// ============================================
// LECTURE PREVIEW
// ============================================

function openLecturePreview(lecture) {
    currentLecture = lecture;
    const modal = document.getElementById('previewModal');
    const content = document.getElementById('previewContent');

    const script = lecture.script;
    const sections = script.sections || [];
    const assessment = script.assessment || {};
    const resources = script.resources || [];

    content.innerHTML = `
        <div style="padding: 1rem;">
            <h1 style="font-size: 2rem; font-weight: 700; margin-bottom: 1rem;">${script.title}</h1>
            
            <div style="display: flex; gap: 2rem; margin-bottom: 2rem; padding: 1rem; background: #f9fafb; border-radius: 8px;">
                <div><strong>Duration:</strong> ${script.duration_minutes} minutes</div>
                <div><strong>Sections:</strong> ${sections.length}</div>
                <div><strong>Model:</strong> ${lecture.model}</div>
            </div>

            ${sections.map(section => `
                <div style="margin-bottom: 2rem; padding: 1.5rem; background: white; border: 2px solid #e5e7eb; border-radius: 12px;">
                    <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">
                        ${section.section_number}. ${section.title}
                    </h2>
                    <p style="color: #6b7280; margin-bottom: 1rem;">⏱️ ${section.duration_minutes} minutes</p>
                    
                    <div style="margin-bottom: 1rem;">
                        <strong>Content:</strong>
                        <p style="margin-top: 0.5rem; line-height: 1.6;">${section.content}</p>
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <strong>Key Points:</strong>
                        <ul style="margin-top: 0.5rem; margin-left: 1.5rem;">
                            ${(section.key_points || []).map(point => `<li>${point}</li>`).join('')}
                        </ul>
                    </div>

                    <div>
                        <strong>Activities:</strong>
                        <ul style="margin-top: 0.5rem; margin-left: 1.5rem;">
                            ${(section.activities || []).map(activity => `<li>${activity}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `).join('')}

            <div style="margin-bottom: 2rem; padding: 1.5rem; background: #fef3c7; border-radius: 12px;">
                <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">📊 Assessment</h2>
                <p><strong>Type:</strong> ${assessment.type}</p>
                <p style="margin-top: 0.5rem;"><strong>Description:</strong> ${assessment.description}</p>
                <div style="margin-top: 1rem;">
                    <strong>Rubric:</strong>
                    <ul style="margin-top: 0.5rem; margin-left: 1.5rem;">
                        ${(assessment.rubric || []).map(item => `<li>${item}</li>`).join('')}
                    </ul>
                </div>
            </div>

            <div style="padding: 1.5rem; background: #e0e7ff; border-radius: 12px;">
                <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">📚 Resources</h2>
                <ul style="margin-top: 0.5rem; margin-left: 1.5rem;">
                    ${resources.map(resource => `<li>${resource}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;

    modal.classList.add('active');
}

function closePreviewModal() {
    document.getElementById('previewModal').classList.remove('active');
}

function openPlayer(lectureId) {
    const lecture = lectures.find(l => l.id === lectureId);
    if (lecture) {
        localStorage.setItem('currentLecture', JSON.stringify(lecture));
        window.open('/player', '_blank');
    }
}

function openLecturePlayer() {
    if (currentLecture) {
        localStorage.setItem('currentLecture', JSON.stringify(currentLecture));
        window.open('/player', '_blank');
    }
}

// ============================================
// EXPORT
// ============================================

function exportLecturePDF() {
    if (!currentLecture) return;

    showToast('PDF export feature coming soon!', 'info');
    // TODO: Implement PDF export using jsPDF
}

// ============================================
// DELETE
// ============================================

async function deleteDocument(id) {
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }

    try {
        await API.deleteContent(id);
        showToast('Document deleted successfully', 'success');
        await loadDocuments();
    } catch (error) {
        console.error('Delete error:', error);
        showToast('Failed to delete document: ' + error.message, 'error');
    }
}

function deleteLecture(id) {
    if (!confirm('Are you sure you want to delete this lecture?')) {
        return;
    }

    lectures = lectures.filter(l => l.id !== id);
    saveLectures();
    loadLectures();
    showToast('Lecture deleted successfully', 'success');
}

// ============================================
// UTILITIES
// ============================================

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');

    toastMessage.textContent = message;
    toast.className = 'toast show ' + type;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
    window.location.href = '/login';
}

document.addEventListener('DOMContentLoaded', () => {
    console.log("Video Generator JS Loaded - Checking token...");
    document.body.style.background = "linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%)"; // Ensure background is set

    const API_BASE = '/api'; 
    const TOKEN_KEY = 'access_token';

    // Check Authentication
    let token = localStorage.getItem(TOKEN_KEY);
    
    console.log("[Token Check] Token from localStorage:", token ? token.substring(0, 20) + "..." : "NOT FOUND");
    
    if (!token) {
        console.warn("[Auth] No token found, redirecting to login...");
        // Give user 2 seconds to see console, then redirect
        setTimeout(() => {
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }, 500);
        // Still proceed with page setup in case they cancel nav
    } else {
        console.log("[Auth] Token verified: " + token.substring(0, 10) + "...");
    }

    // ============================================================
    // DOM Elements with Safety Checks
    // ============================================================
    const getEl = (id) => document.getElementById(id);

    const topicInput = getEl('topic-input');
    const textInput = getEl('text-input');
    const charCount = getEl('char-count');
    const fileInput = getEl('file-input');
    const uploadArea = getEl('upload-area');
    const fileInfo = getEl('file-info');
    const fileName = getEl('file-name');
    const removeFileBtn = getEl('remove-file');
    const generateBtn = getEl('generate-btn');

    // Teacher image elements
    const teacherImageInput = getEl('teacher-image-input');
    const teacherUploadArea = getEl('teacher-upload-area');
    const teacherPreview = getEl('teacher-preview');

    // Colab/HeyGen UI elements
    const colabBar = getEl('colab-bar');
    const colabStatusText = getEl('colab-status-text');

    // Progress/Result elements
    const inputSection = document.querySelector('.input-section');
    const progressSection = getEl('progress-section');
    const progressFill = getEl('progress-fill');
    const progressMessage = getEl('progress-message');
    const resultSection = getEl('result-section');
    const resultMethodInfo = getEl('result-method-info');
    const videoPlayer = getEl('video-player');
    const videoSource = getEl('video-source');
    const downloadBtn = getEl('download-btn');
    const generateAnotherBtn = getEl('generate-another');

    const toast = getEl('toast');
    const toastIcon = getEl('toast-icon');
    const toastMessage = getEl('toast-message');

    // ============================================================
    // State
    // ============================================================
    let currentFile = null;
    let teacherImage = null;
    let pollInterval = null;

    // Safety: If core elements are missing, log error but don't crash
    if (!generateBtn || !topicInput) {
        console.error("Critical DOM elements missing. Check video_generator.html");
        return;
    }

    // ============================================================
    // Event Listeners
    // ============================================================

    // Teacher Image Upload
    if (teacherImageInput) {
        teacherImageInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                teacherImage = e.target.files[0];
                const reader = new FileReader();
                reader.onload = (ev) => {
                    if (teacherPreview) teacherPreview.innerHTML = `<img src="${ev.target.result}" alt="Teacher Photo">`;
                };
                reader.readAsDataURL(teacherImage);
                showToast('Teacher photo loaded!', 'success');
            }
        });
    }

    // Character Counter
    if (textInput && charCount) {
        textInput.addEventListener('input', () => {
            charCount.textContent = textInput.value.length;
        });
    }

    // File Upload Handlers
    if (uploadArea && fileInput) {
        uploadArea.addEventListener('click', () => fileInput.click());

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) handleFileSelect(files[0]);
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) handleFileSelect(e.target.files[0]);
        });
    }

    function handleFileSelect(file) {
        currentFile = file;
        if (uploadArea) uploadArea.style.display = 'none';
        if (fileInfo) fileInfo.style.display = 'flex';
        if (fileName) fileName.textContent = file.name;
    }

    // Remove File
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            currentFile = null;
            if (fileInput) fileInput.value = '';
            if (uploadArea) uploadArea.style.display = 'block';
            if (fileInfo) fileInfo.style.display = 'none';
        });
    }

    // Generate Video
    generateBtn.addEventListener('click', async () => {
        if (!topicInput.value.trim()) {
            showToast('Please enter a topic', 'warning');
            return;
        }

        if (!textInput.value.trim() && !currentFile) {
            showToast('Please provide either text or a file', 'warning');
            return;
        }

        // Refresh token from localStorage (in case it changed)
        token = localStorage.getItem(TOKEN_KEY);
        
        if (!token) {
            showToast('Session expired. Please login again.', 'error');
            window.location.href = '/login';
            return;
        }

        const formData = new FormData();
        formData.append('topic', topicInput.value.trim());
        if (textInput.value.trim()) formData.append('text', textInput.value.trim());
        if (currentFile) formData.append('file', currentFile);
        if (teacherImage) formData.append('teacher_image', teacherImage);

        try {
            showProgress();
            updateProgress(10, 'Initializing...');

            console.log("[Generate] Sending request to", `${API_BASE}/video/generate-avatar`);
            console.log("[Generate] Token:", token.substring(0, 20) + "...");

            const response = await fetch(`${API_BASE}/video/generate-avatar`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            console.log("[Generate] Response status:", response.status);

            if (response.status === 401) {
                console.error("[Generate] 401 Unauthorized - token invalid or expired");
                window.location.href = '/login';
                throw new Error('Session expired. Please login again.');
            }

            if (response.status === 403) {
                const errData = await response.json();
                throw new Error('Access denied: ' + (errData.detail || 'Check user role'));
            }

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log("[Generate] Success! Job ID:", data.video_id);
            startPolling(data.video_id);

        } catch (error) {
            console.error("[Generate] Error:", error);
            showToast(error.message, 'error');
            hideProgress();
        }
    });

    // Polling Logic
    function startPolling(jobId) {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_BASE}/video/status/${jobId}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (response.status === 401) {
                    window.location.href = '/login';
                    return;
                }

                if (!response.ok) return;

                const statusData = await response.json();
                updateProgress(statusData.progress, statusData.message);

                if (statusData.status === 'completed') {
                    clearInterval(pollInterval);
                    finishGeneration(statusData);
                } else if (statusData.status === 'failed') {
                    clearInterval(pollInterval);
                    showToast(`Generation Failed: ${statusData.message}`, 'error');
                    hideProgress();
                }
            } catch (e) {
                console.warn("Polling error:", e);
            }
        }, 2000);
    }

    function finishGeneration(data) {
        if (progressSection) progressSection.style.display = 'none';
        if (resultSection) resultSection.style.display = 'block';

        const videoUrl = data.download_url;
        const method = data.message || '';
        let badgeClass = 'echomimic';
        let badgeText = '✨ HeyGen API (Talking Photo & Lip Sync)';
        
        if (method.includes('static') || method.includes('styled')) {
            badgeClass = 'static';
            badgeText = 'Static Fallback';
        }
        
        if (resultMethodInfo) resultMethodInfo.innerHTML = `<span class="method-badge ${badgeClass}">${badgeText}</span>`;
        if (videoSource) videoSource.src = videoUrl;
        if (videoPlayer) videoPlayer.load();

        if (downloadBtn) {
            downloadBtn.onclick = () => {
                const a = document.createElement('a');
                a.href = videoUrl;
                a.download = `lecture_${data.video_id || 'video'}.mp4`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            };
        }
        showToast('Video generated successfully!', 'success');
    }

    function showProgress() {
        if (inputSection) inputSection.style.display = 'none';
        if (resultSection) resultSection.style.display = 'none';
        if (progressSection) {
            progressSection.style.display = 'block';
            if (progressFill) progressFill.style.width = '0%';
        }
    }

    function hideProgress() {
        if (progressSection) progressSection.style.display = 'none';
        if (inputSection) inputSection.style.display = 'block';
    }

    function updateProgress(percent, message) {
        if (progressFill) progressFill.style.width = `${percent}%`;
        if (progressMessage) progressMessage.textContent = message;

        document.querySelectorAll('.step').forEach((step, idx) => {
            step.classList.remove('active', 'completed');
            if (percent > 25 && idx === 0) step.classList.add('completed');
            if (percent > 40 && idx === 1) step.classList.add('completed');
            if (percent > 75 && idx === 2) step.classList.add('completed');
            if (percent === 100) step.classList.add('completed');

            if (percent <= 25 && idx === 0) step.classList.add('active');
            if (percent > 25 && percent <= 40 && idx === 1) step.classList.add('active');
            if (percent > 40 && percent <= 75 && idx === 2) step.classList.add('active');
            if (percent > 75 && percent < 100 && idx === 3) step.classList.add('active');
        });
    }

    if (generateAnotherBtn) {
        generateAnotherBtn.addEventListener('click', () => {
            if (resultSection) resultSection.style.display = 'none';
            if (inputSection) inputSection.style.display = 'block';

            if (topicInput) topicInput.value = '';
            if (textInput) textInput.value = '';
            currentFile = null;
            if (fileInput) fileInput.value = '';
            if (uploadArea) uploadArea.style.display = 'block';
            if (fileInfo) fileInfo.style.display = 'none';
            if (charCount) charCount.textContent = '0';
            if (videoSource) videoSource.src = '';
            if (resultMethodInfo) resultMethodInfo.innerHTML = '';
        });
    }

    function showToast(message, type = 'success') {
        if (!toast) return;
        toast.className = 'toast ' + type;
        if (toastMessage) toastMessage.textContent = message;
        if (toastIcon) {
            if (type === 'success') toastIcon.textContent = '✓';
            else if (type === 'error') toastIcon.textContent = '✕';
            else toastIcon.textContent = '⚠';
        }
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 4000);
    }
});

/**
 * API Client - Handles all backend communication
 */

const API_BASE_URL = `${window.location.origin}/api`;
const TOKEN_KEY = 'access_token';
const USER_KEY = 'current_user';

/**
 * Store token in localStorage
 */
function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Get stored token
 */
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

/**
 * Clear stored token
 */
function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return getToken() !== null;
}

/**
 * Get auth headers with JWT token
 */
function getAuthHeaders() {
    const token = getToken();
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}

/**
 * API request wrapper
 */
async function apiRequest(endpoint, method = 'GET', body = null, needsAuth = false) {
    const url = `${API_BASE_URL}${endpoint}`;

    const options = {
        method,
        headers: needsAuth ? getAuthHeaders() : { 'Content-Type': 'application/json' }
    };

    if (body && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(url, options);

        if (response.status === 401) {
            clearToken();
            window.location.href = 'index.html';
            throw new Error('Session expired. Please login again.');
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `API Error: ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

// ============ Auth Endpoints ============

async function registerUser(username, email, password, role) {
    return await apiRequest('/auth/register', 'POST', {
        username,
        email,
        password,
        role
    });
}

async function loginUser(username, password) {
    return await apiRequest('/auth/login', 'POST', {
        username,
        password
    });
}

async function getCurrentUser() {
    return await apiRequest('/auth/me', 'GET', null, true);
}

async function logoutUser() {
    return await apiRequest('/auth/logout', 'POST', null, true);
}

// ============ Content Management ============

/**
 * Upload PDF content
 */
async function uploadContent(file) {
    const token = getToken();
    const url = `${API_BASE_URL}/content/upload`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }

        return await response.json();
    } catch (error) {
        console.error('Upload error:', error);
        throw error;
    }
}

/**
 * List user's uploaded contents
 */
async function listContents() {
    return await apiRequest('/content/list', 'GET', null, true);
}

/**
 * Delete content
 */
async function deleteContent(contentId) {
    return await apiRequest(`/content/${contentId}`, 'DELETE', null, true);
}

/**
 * Get RAG processing status
 */
async function getRAGStatus(contentId) {
    return await apiRequest(`/content/rag/status/${contentId}`, 'GET', null, true);
}

// ============ Lecture Generation ============

/**
 * Generate lecture script from content
 */
async function generateLecture(contentId, objectives, title = null) {
    const payload = {
        content_id: contentId,
        objectives: objectives
    };

    if (title) {
        payload.title = title;
    }

    return await apiRequest('/lecture/generate', 'POST', payload, true);
}

/**
 * Generate quiz from content
 */
async function generateQuiz(contentId, numQuestions = 5, difficulty = 'medium') {
    return await apiRequest('/quiz/generate', 'POST', {
        content_id: contentId,
        num_questions: numQuestions,
        difficulty: difficulty
    }, true);
}

/**
 * Ask question using RAG
 */
async function askQuestion(contentId, question, numResults = 5) {
    return await apiRequest('/rag/ask', 'POST', {
        content_id: contentId,
        question: question,
        num_results: numResults
    }, true);
}

// ============ Classroom Sessions ============

async function startClassroomSession(contentId, sessionName) {
    // TODO: Implement in Phase 6
    return await apiRequest('/teacher/classroom/start', 'POST', {
        content_id: contentId,
        session_name: sessionName
    }, true);
}

async function endClassroomSession(sessionId) {
    // TODO: Implement in Phase 6
    return await apiRequest(`/teacher/classroom/end/${sessionId}`, 'POST', null, true);
}

async function submitFrame(sessionId, frameData) {
    // TODO: Implement in Phase 7
}

// ============ Dashboard ============

async function getDashboardSessions() {
    // TODO: Implement in Phase 8
    return await apiRequest('/teacher/dashboard/sessions', 'GET', null, true);
}

// ============ Student Features ============

async function submitQuizAnswer(questionId, selectedAnswer) {
    // TODO: Implement in Phase 9
}

async function submitNote(contentId, noteContent) {
    // TODO: Implement in Phase 9
}

// ============ Export API Object ============

const API = {
    // Auth
    register: registerUser,
    login: loginUser,
    getCurrentUser: getCurrentUser,
    logout: logoutUser,

    // Content
    uploadContent: uploadContent,
    listContents: listContents,
    deleteContent: deleteContent,
    getRAGStatus: getRAGStatus,

    // Generation
    generateLecture: generateLecture,
    generateQuiz: generateQuiz,
    askQuestion: askQuestion,

    // Sessions
    startClassroomSession: startClassroomSession,
    endClassroomSession: endClassroomSession,

    // Dashboard
    getDashboardSessions: getDashboardSessions,

    // Utils
    isAuthenticated: isAuthenticated,
    setToken: setToken,
    getToken: getToken,
    clearToken: clearToken
};

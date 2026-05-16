/**
 * Teacher Dashboard - Functionality and API Integration
 */

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check authentication - but don't redirect in a loop
    const user = getCurrentUserInfo();

    if (!user) {
        // Not logged in - redirect to login ONCE
        console.log('Not authenticated, redirecting to login');
        window.location.href = '/login';
        return; // Stop execution
    }

    // Check role - show error instead of redirecting
    if (user.role !== 'teacher' && user.role !== 'admin') {
        document.body.innerHTML = `
            <div style="text-align:center; padding:50px; color:#fff;">
                <h1>Access Denied</h1>
                <p>This dashboard is for teachers and admins only.</p>
                <p>Your role: ${user.role}</p>
                <a href="/login" style="color:#667eea;">Go to Login</a>
            </div>
        `;
        return; // Stop execution
    }

    // User is authenticated and has correct role - proceed
    console.log('User authenticated:', user.username, 'Role:', user.role);

    // Display user info
    displayUserName();

    // Load dashboard data
    loadTeacherStats();
    loadRecentContent();
    loadRecentActivities();

    // Set up event listeners
    setupEventListeners();
});

/**
 * Display user name in navbar
 */
function displayUserName() {
    const user = getCurrentUserInfo();
    if (user) {
        document.getElementById('userName').textContent = user.username;
    }
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }

    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshDashboard);
    }
}

/**
 * Load teacher statistics
 */
async function loadTeacherStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/teacher/stats`, {
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load statistics');
        }

        const stats = await response.json();

        // Update stat cards
        document.getElementById('totalContent').textContent = stats.total_content;
        document.getElementById('totalSessions').textContent = stats.total_sessions;
        document.getElementById('totalStudents').textContent = stats.total_students;
        document.getElementById('totalAssessments').textContent = stats.total_assessments;

        // Update dynamic stats
        document.getElementById('recentUploads').textContent =
            `+${stats.recent_uploads} this week`;
        document.getElementById('recentUploads').className =
            stats.recent_uploads > 0 ? 'stat-change positive' : 'stat-change';

        document.getElementById('activeSessions').textContent =
            `${stats.active_sessions} active`;

    } catch (error) {
        console.error('Error loading teacher stats:', error);
        showToast('Failed to load statistics', 'error');
    }
}

/**
 * Load recent content
 */
async function loadRecentContent() {
    const contentList = document.getElementById('recentContentList');

    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/content/list`, {
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load content');
        }

        const data = await response.json();
        const content = data.content || [];

        if (content.length === 0) {
            contentList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📄</div>
                    <h3>No content yet</h3>
                    <p>Upload your first document to get started</p>
                </div>
            `;
            return;
        }

        // Display top 5 recent content items
        contentList.innerHTML = content.slice(0, 5).map(item => `
            <div class="content-item" onclick="window.location.href='/lectures'">
                <div class="content-item-left">
                    <div class="content-item-icon">${getFileIcon(item.file_type)}</div>
                    <div class="content-item-info">
                        <h4>${item.filename}</h4>
                        <p>${item.file_type || 'Document'}</p>
                    </div>
                </div>
                <div class="content-item-meta">
                    <div class="content-item-size">${formatFileSize(item.file_size)}</div>
                    <div class="content-item-date">${formatDate(item.upload_date)}</div>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading recent content:', error);
        contentList.innerHTML = `
            <div class="empty-state">
                <p>Failed to load content</p>
            </div>
        `;
    }
}

/**
 * Load recent activities
 */
async function loadRecentActivities() {
    const timeline = document.getElementById('activityTimeline');

    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/recent-activities?limit=5`, {
            headers: {
                'Authorization': `Bearer ${getToken()}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load activities');
        }

        const data = await response.json();
        const activities = data.activities || [];

        if (activities.length === 0) {
            timeline.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <h3>No recent activities</h3>
                    <p>Your activity log will appear here</p>
                </div>
            `;
            return;
        }

        timeline.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon">${getActivityIcon(activity.action)}</div>
                <div class="activity-content">
                    <h4>${activity.action}</h4>
                    <p>${activity.resource_type} | ${activity.details || 'No details'}</p>
                    <div class="activity-time">${formatDate(activity.timestamp)}</div>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading activities:', error);
        timeline.innerHTML = `
            <div class="empty-state">
                <p>Failed to load activities</p>
            </div>
        `;
    }
}

/**
 * Refresh dashboard data
 */
async function refreshDashboard() {
    showToast('Refreshing dashboard...', 'info');
    await Promise.all([
        loadTeacherStats(),
        loadRecentContent(),
        loadRecentActivities()
    ]);
    showToast('Dashboard updated!', 'success');
}

/**
 * Helper: Get file icon based on file type
 */
function getFileIcon(fileType) {
    const icons = {
        'pdf': '📄',
        'docx': '📝',
        'txt': '📃',
        'md': '📋'
    };
    return icons[fileType] || '📄';
}

/**
 * Helper: Format file size
 */
function formatFileSize(bytes) {
    if (!bytes) return 'Unknown';
    const kb = bytes / 1024;
    const mb = kb / 1024;

    if (mb >= 1) {
        return `${mb.toFixed(2)} MB`;
    }
    return `${kb.toFixed(2)} KB`;
}

/**
 * Helper: Format date to relative time
 */
function formatDate(dateString) {
    if (!dateString) return 'Unknown';

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

/**
 * Helper: Get activity icon
 */
function getActivityIcon(action) {
    const icons = {
        'upload': '📤',
        'generate': '🎓',
        'create': '✨',
        'update': '✏️',
        'delete': '🗑️',
        'login': '🔐',
        'logout': '👋'
    };

    const key = action.toLowerCase().split(' ')[0];
    return icons[key] || '📊';
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');

    if (!toast || !toastMessage) return;

    toastMessage.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

/**
 * Student Dashboard - Functionality and API Integration
 */

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUserInfo();

    if (!user) {
        console.log('Not authenticated, redirecting to login');
        window.location.href = '/login';
        return;
    }

    if (user.role !== 'student') {
        document.body.innerHTML = `<div style="text-align:center; padding:50px; color:#fff;"><h1>Access Denied</h1><p>Student dashboard only</p><a href="/login" style="color:#667eea;">Go to Login</a></div>`;
        return;
    }

    displayUserName();
    loadStudentStats();
    loadRecentActivities();
    setupEventListeners();
});

function displayUserName() {
    const user = getCurrentUserInfo();
    if (user) {
        document.getElementById('userName').textContent = user.username;
    }
}

function setupEventListeners() {
    document.getElementById('logoutBtn')?.addEventListener('click', handleLogout);
    document.getElementById('refreshBtn')?.addEventListener('click', refreshDashboard);
}

async function loadStudentStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/student/stats`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });

        if (!response.ok) throw new Error('Failed to load statistics');

        const stats = await response.json();

        document.getElementById('enrolledCourses').textContent = stats.enrolled_courses;
        document.getElementById('completedAssessments').textContent = stats.completed_assessments;
        document.getElementById('averageScore').textContent = `${stats.average_score}%`;
        document.getElementById('studyTime').textContent = stats.study_time_minutes;

    } catch (error) {
        console.error('Error loading student stats:', error);
        showToast('Failed to load statistics', 'error');
    }
}

async function loadRecentActivities() {
    const timeline = document.getElementById('activityTimeline');

    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/recent-activities?limit=5`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });

        if (!response.ok) throw new Error('Failed to load activities');

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
                    <p>${activity.resource_type}</p>
                    <div class="activity-time">${formatDate(activity.timestamp)}</div>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading activities:', error);
        timeline.innerHTML = `<div class="empty-state"><p>Failed to load activities</p></div>`;
    }
}

async function refreshDashboard() {
    showToast('Refreshing dashboard...', 'info');
    await Promise.all([loadStudentStats(), loadRecentActivities()]);
    showToast('Dashboard updated!', 'success');
}

function getActivityIcon(action) {
    const icons = {
        'study': '📚',
        'quiz': '📝',
        'complete': '✅',
        'start': '▶️',
        'login': '🔐'
    };
    const key = action.toLowerCase().split(' ')[0];
    return icons[key] || '📊';
}

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

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    if (!toast || !toastMessage) return;

    toastMessage.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => { toast.className = 'toast'; }, 3000);
}

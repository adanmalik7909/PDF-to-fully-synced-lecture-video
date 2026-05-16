/**
 * Admin Dashboard - System Management and Monitoring
 */

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUserInfo();

    if (!user) {
        console.log('Not authenticated, redirecting to login');
        window.location.href = '/login';
        return;
    }

    if (user.role !== 'admin') {
        document.body.innerHTML = `<div style="text-align:center; padding:50px; color:#fff;"><h1>Access Denied</h1><p>Admin dashboard only</p><a href="/login" style="color:#667eea;">Go to Login</a></div>`;
        return;
    }

    displayUserName();
    loadAdminStats();
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

async function loadAdminStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/admin/stats`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });

        if (!response.ok) throw new Error('Failed to load statistics');

        const stats = await response.json();

        document.getElementById('totalUsers').textContent = stats.total_users;
        document.getElementById('totalTeachers').textContent = stats.total_teachers;
        document.getElementById('totalStudents').textContent = stats.total_students;
        document.getElementById('totalContent').textContent = stats.total_content;
        document.getElementById('activeToday').textContent = `${stats.active_users_today} active today`;

    } catch (error) {
        console.error('Error loading admin stats:', error);
        showToast('Failed to load statistics', 'error');
    }
}

async function refreshDashboard() {
    showToast('Refreshing dashboard...', 'info');
    await loadAdminStats();
    showToast('Dashboard updated!', 'success');
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    if (!toast || !toastMessage) return;

    toastMessage.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => { toast.className = 'toast'; }, 3000);
}

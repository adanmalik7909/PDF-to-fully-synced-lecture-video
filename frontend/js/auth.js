/**
 * Authentication Logic - Handle login/register/logout
 */

const TOKEN_KEY = 'access_token';
const USER_KEY = 'current_user';

// Login form handler
const loginForm = document.getElementById('loginForm');

// ALWAYS clear token on login page load to prevent stale state
localStorage.removeItem('jwt_token');
localStorage.removeItem('user_info');
localStorage.removeItem(TOKEN_KEY);
localStorage.removeItem(USER_KEY);

if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
}

/**
 * Handle login form submission
 */
async function handleLogin(e) {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const messageEl = document.getElementById('message');

    try {
        messageEl.textContent = 'Logging in...';
        messageEl.className = 'message info';

        // Call login API
        const response = await loginUser(username, password);

        // Store token and user info
        setToken(response.access_token);
        localStorage.setItem(USER_KEY, JSON.stringify({
            id: response.user_id,
            username: response.username,
            email: response.email,
            role: response.role
        }));

        messageEl.textContent = `✓ Login successful! Redirecting...`;
        messageEl.className = 'message success';

        // Redirect based on role
        setTimeout(() => redirectToDashboard(response.role), 1500);

    } catch (error) {
        messageEl.textContent = `✗ Login failed: ${error.message}`;
        messageEl.className = 'message error';
        console.error('Login error:', error);
    }
}

/**
 * Redirect to appropriate dashboard based on user role
 */
function redirectToDashboard(role) {
    if (!role) {
        const user = JSON.parse(localStorage.getItem(USER_KEY) || '{}');
        role = user.role;
    }

    // For demo: teachers go straight to video generator
    const dashboards = {
        'teacher': '/video-generator',
        'admin': '/video-generator',
        'student': '/video-generator'
    };

    const target = dashboards[role] || '/video-generator';
    window.location.href = target;
}

/**
 * Handle logout
 */
async function handleLogout() {
    if (confirm('Are you sure you want to logout?')) {
        try {
            await logoutUser();
        } catch (error) {
            console.warn('Logout API call failed:', error);
        } finally {
            clearToken();
            window.location.href = '/login';
        }
    }
}

/**
 * Get current logged-in user
 */
function getCurrentUserInfo() {
    if (!isAuthenticated()) {
        return null;
    }
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
}

/**
 * Require authentication - redirect to login if not authenticated
 */
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login';
    }
}

/**
 * Display user info in navbar/header
 */
function displayUserInfo() {
    const user = getCurrentUserInfo();
    if (user) {
        const userInfoEl = document.getElementById('userInfo');
        if (userInfoEl) {
            userInfoEl.innerHTML = `
                <span>${user.username} (${user.role})</span>
                <button onclick="handleLogout()" class="btn-logout">Logout</button>
            `;
        }
    }
}

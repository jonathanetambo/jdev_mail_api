// static/js/main.js

const themeToggle = document.getElementById('checkbox');
const currentTheme = localStorage.getItem('theme') || 'dark';

document.documentElement.setAttribute('data-theme', currentTheme);

if (themeToggle) {
    themeToggle.checked = currentTheme === 'dark';

    themeToggle.addEventListener('change', function(e) {
        const theme = e.target.checked ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    });
}

const hamburger = document.getElementById('hamburger');
const navMenu = document.getElementById('navMenu');

if (hamburger && navMenu) {
    hamburger.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        hamburger.classList.toggle('active');
    });
}

function getAuthToken() {
    return localStorage.getItem('access_token');
}

function isAuthenticated() {
    return !!getAuthToken();
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notification-container');

    if (!container) {
        console.log(`[${type}] ${message}`);
        return;
    }

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;

    let icon = '';
    if (type === 'success') icon = '<i class="fas fa-check-circle"></i> ';
    if (type === 'error') icon = '<i class="fas fa-times-circle"></i> ';
    if (type === 'info') icon = '<i class="fas fa-info-circle"></i> ';

    notification.innerHTML = icon + message;
    container.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function logoutUser(event = null) {
    if (event) event.preventDefault();

    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_data');

    showNotification('Déconnexion réussie', 'success');

    setTimeout(() => {
        window.location.href = '/login';
    }, 800);
}

async function apiRequest(url, options = {}) {
    const token = getAuthToken();

    if (!token) {
        console.error('Token absent');
        window.location.href = '/login';
        return null;
    }

    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...(options.headers || {})
    };

    const response = await fetch(url, {
        ...options,
        headers
    });

    if (response.status === 401 || response.status === 422) {
        let errorData = {};

        try {
            errorData = await response.clone().json();
        } catch (e) {}

        console.error('Erreur JWT:', errorData);

        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_data');

        showNotification('Session expirée ou token invalide. Reconnectez-vous.', 'error');

        setTimeout(() => {
            window.location.href = '/login';
        }, 800);

        return null;
    }

    return response;
}

const api = {
    get: function(url) {
        return apiRequest(url, {
            method: 'GET'
        });
    },

    post: function(url, data = {}) {
        return apiRequest(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    put: function(url, data = {}) {
        return apiRequest(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    delete: function(url) {
        return apiRequest(url, {
            method: 'DELETE'
        });
    }
};

function updateAuthLinks() {
    const token = getAuthToken();
    const authLinksDiv = document.getElementById('authLinks');

    if (!authLinksDiv) return;

    if (token) {
        authLinksDiv.innerHTML = `
            <a href="/dashboard" class="nav-link">
                <i class="fas fa-tachometer-alt"></i> Dashboard
            </a>
            <a href="#" class="nav-link" onclick="logoutUser(event)">
                <i class="fas fa-sign-out-alt"></i> Logout
            </a>
        `;
    } else {
        authLinksDiv.innerHTML = `
            <a href="/login" class="nav-link">
                <i class="fas fa-sign-in-alt"></i> Login
            </a>
            <a href="/register" class="btn-primary-small">
                <i class="fas fa-user-plus"></i> Sign Up
            </a>
        `;
    }
}

function checkPageAuth() {
    const token = getAuthToken();
    const publicPages = ['/', '/login', '/register', '/features', '/pricing', '/docs'];
    const currentPath = window.location.pathname;

    if (!token && !publicPages.includes(currentPath)) {
        window.location.href = '/login';
        return false;
    }

    if (token && (currentPath === '/login' || currentPath === '/register')) {
        window.location.href = '/dashboard';
        return false;
    }

    return true;
}

function copyToClipboard(textOrElementId) {
    let text = textOrElementId;

    const element = document.getElementById(textOrElementId);
    if (element) {
        text = element.textContent;
    }

    navigator.clipboard.writeText(text);
    showNotification('Copié dans le presse-papiers', 'success');
}

document.addEventListener('DOMContentLoaded', () => {
    updateAuthLinks();
    checkPageAuth();
});

window.api = api;
window.apiRequest = apiRequest;
window.showNotification = showNotification;
window.copyToClipboard = copyToClipboard;
window.isAuthenticated = isAuthenticated;
window.getAuthToken = getAuthToken;
window.logoutUser = logoutUser;
window.updateAuthLinks = updateAuthLinks;
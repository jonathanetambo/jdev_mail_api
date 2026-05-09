// static/js/dashboard.js
class DashboardManager {
    constructor() {
        this.stats = {
            totalEmails: 0,
            totalSites: 0,
            successRate: 100,
            avgTime: 120
        };
    }

    async loadStats() {
        try {
            console.log('Loading stats...');
            const response = await api.get('/api/stats');
            
            console.log('Stats response:', response);
            
            if (response && response.ok) {
                const data = await response.json();
                console.log('Stats data:', data);
                
                this.stats = {
                    totalEmails: data.total_emails || 0,
                    totalSites: data.total_sites || 0,
                    successRate: parseFloat(data.success_rate) || 100,
                    avgTime: data.avg_time || '120'
                };
                this.updateStatsUI();
            } else if (response && response.status === 401) {
                console.log('Unauthorized, redirecting to login...');
                window.location.href = '/login';
            } else {
                console.error('Failed to load stats:', response ? response.status : 'No response');
                this.showError('Failed to load statistics');
            }
        } catch (error) {
            console.error('Error loading stats:', error);
            this.showError('Network error loading statistics');
        }
    }

    updateStatsUI() {
        const totalEmailsEl = document.getElementById('totalEmails');
        const totalSitesEl = document.getElementById('totalSites');
        const successRateEl = document.getElementById('successRate');
        const avgTimeEl = document.getElementById('avgTime');
        
        if (totalEmailsEl) totalEmailsEl.textContent = this.stats.totalEmails;
        if (totalSitesEl) totalSitesEl.textContent = this.stats.totalSites;
        if (successRateEl) successRateEl.textContent = `${this.stats.successRate}%`;
        if (avgTimeEl) avgTimeEl.textContent = `${this.stats.avgTime}ms`;
        
        const progressBar = document.getElementById('successProgress');
        if (progressBar) {
            progressBar.style.width = `${this.stats.successRate}%`;
        }
    }

    showError(message) {
        const container = document.getElementById('sitesList');
        if (container) {
            container.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>${message}</p>
                    <button onclick="location.reload()" class="btn-small">Retry</button>
                </div>
            `;
        }
        showNotification(message, 'error');
    }

    async loadUserData() {
        try {
            const userData = localStorage.getItem('user_data');
            if (userData) {
                const user = JSON.parse(userData);
                const userNameEl = document.getElementById('userName');
                const userEmailEl = document.getElementById('userEmail');
                const welcomeNameEl = document.getElementById('welcomeName');
                
                if (userNameEl) userNameEl.textContent = user.username;
                if (userEmailEl) userEmailEl.textContent = user.email;
                if (welcomeNameEl) welcomeNameEl.textContent = user.username;
            } else {
                // Essayer de récupérer les infos utilisateur depuis l'API
                const response = await api.get('/auth/me');
                if (response && response.ok) {
                    const data = await response.json();
                    const user = data.user;
                    localStorage.setItem('user_data', JSON.stringify(user));
                    this.loadUserData(); // Recharger
                }
            }
        } catch (error) {
            console.error('Error loading user data:', error);
        }
    }

    async refreshDashboard() {
        showNotification('Refreshing dashboard...', 'info');
        await this.loadStats();
        if (window.sitesManager) {
            await window.sitesManager.loadSites();
        }
        showNotification('Dashboard refreshed!', 'success');
    }

    initNavigation() {
        const sidebarLinks = document.querySelectorAll('.sidebar-link');
        if (sidebarLinks) {
            sidebarLinks.forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const section = link.dataset.section;
                    
                    sidebarLinks.forEach(l => l.classList.remove('active'));
                    link.classList.add('active');
                    
                    const dashboardSections = document.querySelectorAll('.dashboard-section');
                    dashboardSections.forEach(s => s.classList.remove('active'));
                    
                    const activeSection = document.getElementById(section);
                    if (activeSection) {
                        activeSection.classList.add('active');
                    }
                    
                    if (section === 'logs' && window.logsManager) {
                        window.logsManager.loadLogs();
                    }
                    if (section === 'analytics' && window.analyticsManager) {
                        window.analyticsManager.loadAnalytics();
                    }
                });
            });
        }
    }

    initModals() {
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
            }
        };
    }

    async init() {
        console.log('Initializing dashboard...');
        await this.loadUserData();
        await this.loadStats();
        if (window.sitesManager) {
            await window.sitesManager.loadSites();
        }
        this.initNavigation();
        this.initModals();
    }
}

// Initialiser le dashboard
const dashboardManager = new DashboardManager();

// Fonctions globales pour les modals
function openCreateSiteModal() {
    const modal = document.getElementById('createSiteModal');
    if (modal) modal.style.display = 'block';
}

function closeCreateSiteModal() {
    const modal = document.getElementById('createSiteModal');
    if (modal) modal.style.display = 'none';
    const form = document.getElementById('createSiteForm');
    if (form) form.reset();
}

function closeViewKeysModal() {
    const modal = document.getElementById('viewKeysModal');
    if (modal) modal.style.display = 'none';
}

function closeViewLogModal() {
    const modal = document.getElementById('viewLogModal');
    if (modal) modal.style.display = 'none';
}

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        const text = element.textContent;
        navigator.clipboard.writeText(text);
        showNotification('Copied to clipboard!', 'success');
    }
}

function refreshDashboard() {
    dashboardManager.refreshDashboard();
}

// Formulaire de création de site
const createSiteForm = document.getElementById('createSiteForm');
if (createSiteForm) {
    createSiteForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const nameInput = document.getElementById('siteName');
        const domainInput = document.getElementById('siteDomain');
        
        if (!nameInput || !domainInput) return;
        
        const name = nameInput.value.trim();
        const domain = domainInput.value.trim();
        
        if (!name || !domain) {
            showNotification('Please fill in all fields', 'error');
            return;
        }
        
        if (window.sitesManager) {
            const success = await window.sitesManager.createSite(name, domain);
            if (success) {
                closeCreateSiteModal();
                dashboardManager.loadStats();
            }
        } else {
            showNotification('Sites manager not initialized', 'error');
        }
    });
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing dashboard...');
    dashboardManager.init();
});
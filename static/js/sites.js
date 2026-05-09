// static/js/sites.js

const API_BASE_URL = window.API_BASE_URL || "";

function getToken() {
    return (
        localStorage.getItem("access_token") ||
        localStorage.getItem("token") ||
        localStorage.getItem("jwt") ||
        sessionStorage.getItem("access_token") ||
        ""
    );
}

async function authRequest(url, options = {}) {
    const token = getToken();

    if (!token) {
        console.error("Aucun token JWT trouvé dans localStorage.");
        window.location.href = "/login";
        return null;
    }

    const headers = {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
        ...(options.headers || {})
    };

    const response = await fetch(`${API_BASE_URL}${url}`, {
        ...options,
        headers
    });

    if (response.status === 401 || response.status === 422) {
        const errorData = await response.json().catch(() => ({}));
        console.error("Erreur JWT:", errorData);

        localStorage.removeItem("access_token");
        localStorage.removeItem("token");
        localStorage.removeItem("jwt");

        showNotification("Session expirée ou token invalide. Reconnectez-vous.", "error");
        window.location.href = "/login";
        return null;
    }

    return response;
}

class SitesManager {
    constructor() {
        this.currentSites = [];
    }

    async loadSites() {
        try {
            const response = await authRequest("/api/sites", {
                method: "GET"
            });

            if (!response) return [];

            const data = await response.json();

            if (response.ok) {
                this.currentSites = data.sites || [];
                this.renderSites();
                return this.currentSites;
            }

            showNotification(data.error || "Erreur lors du chargement des sites", "error");

        } catch (error) {
            console.error("Error loading sites:", error);
            showNotification("Erreur réseau lors du chargement des sites", "error");
        }

        return [];
    }

    renderSites() {
        const container = document.getElementById("sitesList");
        if (!container) return;

        if (!this.currentSites.length) {
            container.innerHTML = `
                <div class="no-data">
                    <i class="fas fa-inbox"></i>
                    <p>Aucun site pour le moment. Cliquez sur "New Site" pour créer un site.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.currentSites.map(site => `
            <div class="site-card">
                <div class="site-header">
                    <h3><i class="fas fa-globe"></i> ${this.escapeHtml(site.name)}</h3>
                    <span class="site-status ${site.is_active ? "active" : "inactive"}">
                        <i class="fas ${site.is_active ? "fa-check-circle" : "fa-times-circle"}"></i>
                        ${site.is_active ? "Active" : "Inactive"}
                    </span>
                </div>

                <div class="site-details">
                    <div class="detail-item">
                        <label><i class="fas fa-id-card"></i> Site ID:</label>
                        <code>${this.escapeHtml(site.site_id)}</code>
                    </div>

                    <div class="detail-item">
                        <label><i class="fas fa-link"></i> Domain:</label>
                        <span>${this.escapeHtml(site.domain)}</span>
                    </div>

                    <div class="detail-item">
                        <label><i class="fas fa-envelope"></i> Emails Sent:</label>
                        <span>${site.emails_sent || 0}</span>
                    </div>

                    <div class="detail-item">
                        <label><i class="fas fa-calendar"></i> Created:</label>
                        <span>${site.created_at ? new Date(site.created_at).toLocaleDateString() : "-"}</span>
                    </div>
                </div>

                <div class="site-actions">
                    <button class="btn-small" onclick="sitesManager.viewKeys(${site.id})">
                        <i class="fas fa-key"></i> View Keys
                    </button>

                    <button class="btn-small" onclick="sitesManager.regenerateKeys(${site.id})">
                        <i class="fas fa-sync-alt"></i> Regenerate
                    </button>

                    <button class="btn-small btn-danger" onclick="sitesManager.deleteSite(${site.id})">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        `).join("");
    }

    async createSite(name, domain) {
        try {
            const response = await authRequest("/api/sites", {
                method: "POST",
                body: JSON.stringify({ name, domain })
            });

            if (!response) return false;

            const data = await response.json();

            if (response.ok) {
                showNotification("Site créé avec succès !", "success");
                await this.loadSites();

                if (data.site && data.site.id) {
                    setTimeout(() => {
                        this.viewKeys(data.site.id);
                    }, 500);
                }

                return true;
            }

            showNotification(data.error || "Erreur lors de la création du site", "error");
            return false;

        } catch (error) {
            console.error("Error creating site:", error);
            showNotification("Erreur réseau. Veuillez réessayer.", "error");
            return false;
        }
    }

    async viewKeys(siteId) {
        try {
            const response = await authRequest(`/api/sites/${siteId}/keys`, {
                method: "GET"
            });

            if (!response) return;

            const data = await response.json();

            if (!response.ok) {
                showNotification(data.error || "Erreur lors du chargement des clés", "error");
                return;
            }

            document.getElementById("viewSiteId").textContent = data.site_id;
            document.getElementById("viewPublicKey").textContent = data.public_key;
            document.getElementById("viewSecretKey").textContent = data.secret_key;

            const curlExample = `curl -X POST ${API_BASE_URL}/api/send-email \\
  -H "Content-Type: application/json" \\
  -d '{
    "site_id": "${data.site_id}",
    "public_key": "${data.public_key}",
    "secret_key": "${data.secret_key}",
    "to": "user@example.com",
    "subject": "Hello from JDev Mail",
    "html_content": "<h1>Welcome!</h1>"
  }'`;

            document.getElementById("curlExample").textContent = curlExample;
            document.getElementById("viewKeysModal").style.display = "block";

        } catch (error) {
            console.error("Error loading keys:", error);
            showNotification("Erreur lors du chargement des clés", "error");
        }
    }

    async regenerateKeys(siteId) {
        if (!confirm("La régénération va invalider les anciennes clés API. Continuer ?")) return;

        try {
            const response = await authRequest(`/api/sites/${siteId}/regenerate-keys`, {
                method: "POST"
            });

            if (!response) return;

            const data = await response.json();

            if (response.ok) {
                showNotification("Clés régénérées avec succès !", "success");
                await this.loadSites();
                await this.viewKeys(siteId);
            } else {
                showNotification(data.error || "Erreur lors de la régénération des clés", "error");
            }

        } catch (error) {
            console.error("Error regenerating keys:", error);
            showNotification("Erreur lors de la régénération des clés", "error");
        }
    }

    async deleteSite(siteId) {
        if (!confirm("Voulez-vous vraiment supprimer ce site ? Cette action est irréversible.")) return;

        try {
            const response = await authRequest(`/api/sites/${siteId}`, {
                method: "DELETE"
            });

            if (!response) return;

            const data = await response.json();

            if (response.ok) {
                showNotification("Site supprimé avec succès", "success");
                await this.loadSites();

                if (window.dashboardManager) {
                    window.dashboardManager.loadStats();
                }
            } else {
                showNotification(data.error || "Erreur lors de la suppression du site", "error");
            }

        } catch (error) {
            console.error("Error deleting site:", error);
            showNotification("Erreur lors de la suppression du site", "error");
        }
    }

    escapeHtml(text) {
        if (text === null || text === undefined) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
}

const sitesManager = new SitesManager();
window.sitesManager = sitesManager;
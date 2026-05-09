// static/js/logs.js
class LogsManager {
    constructor() {
        this.currentLogs = [];
    }

    async loadLogs() {
        const tbody = document.getElementById('logsTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
        }
        
        try {
            const response = await api.get('/api/logs');
            if (response && response.ok) {
                const data = await response.json();
                this.currentLogs = data.logs || [];
                this.renderLogs();
            }
        } catch (error) {
            console.error('Error loading logs:', error);
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="6" class="no-data">Failed to load logs</td></tr>';
            }
        }
    }

    renderLogs() {
        const tbody = document.getElementById('logsTableBody');
        if (!tbody) return;

        if (!this.currentLogs.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="no-data">No logs found</td></tr>';
            return;
        }

        tbody.innerHTML = this.currentLogs.map(log => `
            <tr>
                <td><i class="fas fa-calendar-alt"></i> ${new Date(log.sent_at).toLocaleString()}</td>
                <td><i class="fas fa-globe"></i> ${this.escapeHtml(log.site_name || 'N/A')}</td>
                <td><i class="fas fa-envelope"></i> ${this.escapeHtml(log.recipient)}</td>
                <td><i class="fas fa-tag"></i> ${this.escapeHtml(log.subject)}</td>
                <td><span class="status-badge status-${log.status}">
                    <i class="fas ${log.status === 'sent' ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                    ${log.status}
                </span></td>
                <td>
                    <button class="btn-icon" onclick="logsManager.viewDetails(${log.id})" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-icon" onclick="logsManager.decryptLog(${log.id})" title="Decrypt Log">
                        <i class="fas fa-lock-open"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    async viewDetails(logId) {
        try {
            const response = await api.get(`/api/logs/${logId}`);
            if (response && response.ok) {
                const data = await response.json();
                const logDetails = document.getElementById('logDetails');
                if (logDetails) {
                    logDetails.innerHTML = `
                        <div class="log-detail-item">
                            <label><i class="fas fa-envelope"></i> Recipient:</label>
                            <span>${this.escapeHtml(data.recipient)}</span>
                        </div>
                        <div class="log-detail-item">
                            <label><i class="fas fa-tag"></i> Subject:</label>
                            <span>${this.escapeHtml(data.subject)}</span>
                        </div>
                        <div class="log-detail-item">
                            <label><i class="fas fa-info-circle"></i> Status:</label>
                            <span class="status-badge status-${data.status}">${data.status}</span>
                        </div>
                        <div class="log-detail-item">
                            <label><i class="fas fa-calendar"></i> Sent At:</label>
                            <span>${new Date(data.sent_at).toLocaleString()}</span>
                        </div>
                        <div class="log-detail-item">
                            <label><i class="fas fa-network-wired"></i> IP Address:</label>
                            <span>${data.ip_address}</span>
                        </div>
                        ${data.error_message ? `
                        <div class="log-detail-item">
                            <label><i class="fas fa-exclamation-triangle"></i> Error:</label>
                            <span class="error-text">${this.escapeHtml(data.error_message)}</span>
                        </div>
                        ` : ''}
                    `;
                    document.getElementById('viewLogModal').style.display = 'block';
                }
            }
        } catch (error) {
            showNotification('Error loading log details', 'error');
        }
    }

    async decryptLog(logId) {
        try {
            const response = await api.get(`/api/logs/${logId}/decrypt`);
            if (response && response.ok) {
                const data = await response.json();
                showNotification('Log decrypted successfully!', 'success');
                const logDetails = document.getElementById('logDetails');
                if (logDetails) {
                    logDetails.innerHTML = `
                        <div class="decrypted-log">
                            <h4><i class="fas fa-lock-open"></i> Decrypted Log Content</h4>
                            <pre><code>${JSON.stringify(data.decrypted_log, null, 2)}</code></pre>
                        </div>
                    `;
                    document.getElementById('viewLogModal').style.display = 'block';
                }
            } else {
                showNotification('Failed to decrypt log', 'error');
            }
        } catch (error) {
            showNotification('Error decrypting log', 'error');
        }
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

const logsManager = new LogsManager();
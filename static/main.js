// static/main.js
class OrgPortal {
    constructor() {
        this.state = {
            user: null,
            activeTab: null,
            files: [],
            searchQuery: ''
        };
        // --- Cache DOM elements ---
        this.elements = {
            authSection: document.getElementById('auth-section'),
            mainApp: document.getElementById('main-app'),
            loginBtn: document.getElementById('login-btn'),
            logoutBtn: document.getElementById('logout-btn'),
            userEmail: document.getElementById('user-email'),
            tabsContainer: document.getElementById('tabs-container'),
            tabTitle: document.getElementById('tab-title'),
            tabDescription: document.getElementById('tab-description'),
            fileUpload: document.getElementById('file-upload'),
            uploadBtn: document.getElementById('upload-btn'),
            searchInput: document.getElementById('search-input'),
            searchBtn: document.getElementById('search-btn'),
            filesList: document.getElementById('files-list'),
            loading: document.getElementById('loading'),
            noFiles: document.getElementById('no-files'),
            flashContainer: document.getElementById('flash-container')
        };
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkAuth();
    }

    bindEvents() {
        if (this.elements.loginBtn) {
            this.elements.loginBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log("🖱️ [LOGIN BUTTON] Clicked");
                const authUrl = window.APP_CONFIG?.authUrl;
                if (authUrl) {
                    console.log("🔗 [REDIRECT] Going to:", authUrl);
                    window.location.href = authUrl;
                } else {
                    this.showError("Login URL not available. Please refresh.");
                    console.error("❌ No auth_url found in window.APP_CONFIG");
                }
            });
        }
        if (this.elements.logoutBtn) {
            this.elements.logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                fetch('/logout', { method: 'GET' })
                    .then(() => {
                        window.location.reload();
                    })
                    .catch(err => {
                        console.error("Logout failed:", err);
                        window.location.reload();
                    });
            });
        }
        if (this.elements.uploadBtn) {
            this.elements.uploadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleUpload();
            });
        }
        if (this.elements.searchBtn) {
            this.elements.searchBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.loadFiles();
            });
        }
        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.loadFiles();
                }
            });
        }
    }

    async checkAuth() {
        try {
            console.log("🔍 [AUTH] Checking user authentication...");
            const res = await fetch('/api/user');
            const data = await res.json();
            console.log("👤 [AUTH] User data received:", data);
            if (data.authenticated) {
                this.state.user = data;
                this.showMainApp();
                this.loadTabs();
                if (data.accessible_tabs && data.accessible_tabs.length > 0) {
                    this.setActiveTab(data.accessible_tabs[0]);
                }
            } else {
                this.showAuthSection();
            }
        } catch (err) {
            console.error("❌ [AUTH] Auth check failed:", err);
            this.showAuthSection();
        }
    }

    showAuthSection() {
        console.log("🏠 [UI] Showing auth section");
        if(this.elements.authSection) this.elements.authSection.style.display = 'flex'; // Changed to flex
        if(this.elements.mainApp) this.elements.mainApp.style.display = 'none';
    }

    showMainApp() {
        console.log("📊 [UI] Showing main app");
        if(this.elements.authSection) this.elements.authSection.style.display = 'none';
        if(this.elements.mainApp) this.elements.mainApp.style.display = 'block';
        if(this.elements.userEmail) this.elements.userEmail.textContent = `👤 Logged in as: ${this.state.user.email}`;
    }

    async loadTabs() {
        if (!this.state.user || !this.state.user.accessible_tabs) {
            console.warn("⚠️ [TABS] No user or accessible tabs found");
            return;
        }
        try {
            console.log("📂 [TABS] Loading tab definitions...");
            const res = await fetch('/api/tabs');
            const allTabs = await res.json();
            console.log("🏷️ [TABS] Tab definitions:", allTabs);
            if(this.elements.tabsContainer) this.elements.tabsContainer.innerHTML = '';
            this.state.user.accessible_tabs.forEach(tabKey => {
                const tabDisplayName = allTabs[tabKey] || tabKey;
                const tabEl = document.createElement('a');
                tabEl.href = '#';
                tabEl.className = 'tab';
                tabEl.textContent = tabDisplayName;
                tabEl.dataset.tab = tabKey;
                tabEl.addEventListener('click', (e) => {
                    e.preventDefault();
                    console.log(`📈 [TABS] Switching to tab: ${tabKey}`);
                    this.setActiveTab(tabKey);
                });
                if(this.elements.tabsContainer) this.elements.tabsContainer.appendChild(tabEl);
            });
        } catch (err) {
            console.error("❌ [TABS] Failed to load tabs:", err);
            this.showError("Failed to load navigation tabs.");
        }
    }

    async setActiveTab(tabKey) {
        if (this.state.activeTab === tabKey) return;
        console.log(`📌 [TABS] Setting active tab to: ${tabKey}`);
        this.state.activeTab = tabKey;
        this.updateActiveTabUI();
        this.loadFiles();
    }

    async updateActiveTabUI() {
        if (!this.state.activeTab) return;
        try {
            const res = await fetch('/api/tabs');
            const allTabs = await res.json();
            const activeTabDisplayName = allTabs[this.state.activeTab] || this.state.activeTab;
            if(this.elements.tabTitle) this.elements.tabTitle.textContent = activeTabDisplayName;
            document.querySelectorAll('.tab').forEach(el => {
                el.classList.toggle('active', el.dataset.tab === this.state.activeTab);
            });
        } catch (err) {
            console.error("❌ [UI] Failed to update tab UI:", err);
        }
    }

    async loadFiles() {
        if (!this.state.activeTab) {
            console.warn("⚠️ [FILES] No active tab set, cannot load files.");
            return;
        }
        this.state.searchQuery = this.elements.searchInput ? this.elements.searchInput.value.trim() : '';
        if(this.elements.loading) this.elements.loading.style.display = 'flex'; // Changed to flex for spinner alignment
        if(this.elements.filesList) this.elements.filesList.innerHTML = '';
        if(this.elements.noFiles) this.elements.noFiles.style.display = 'none';
        try {
            console.log(`🗂️ [FILES] Loading files for tab: ${this.state.activeTab}, search: '${this.state.searchQuery}'`);
            let url = `/api/tab/${this.state.activeTab}/files`;
            if (this.state.searchQuery) {
                url += `?q=${encodeURIComponent(this.state.searchQuery)}`;
            }
            const res = await fetch(url);
            if (!res.ok) {
                const errorText = await res.text();
                throw new Error(`HTTP ${res.status}: ${errorText}`);
            }
            const data = await res.json();
            console.log(`📦 [FILES] Files received for ${this.state.activeTab}:`, data);
            if (data.error) {
                this.showError(data.error);
                return;
            }
            this.state.files = data.files || [];
            this.renderFiles();
        } catch (err) {
            console.error("❌ [FILES] Failed to load files:", err);
            this.showError(`Failed to load files: ${err.message}`);
        } finally {
            if(this.elements.loading) this.elements.loading.style.display = 'none';
        }
    }

    renderFiles() {
        if(!this.elements.filesList) return;
        this.elements.filesList.innerHTML = '';
        if (!this.state.files || this.state.files.length === 0) {
            if(this.elements.noFiles) this.elements.noFiles.style.display = 'block';
            return;
        }
        if(this.elements.noFiles) this.elements.noFiles.style.display = 'none';
        this.state.files.forEach(file => {
            const li = document.createElement('li');
            li.className = 'file-item';

            const infoDiv = document.createElement('div');
            infoDiv.className = 'file-info';

            const nameDiv = document.createElement('div');
            nameDiv.className = 'file-name';

            const link = document.createElement('a');
            link.href = file.webViewLink;
            link.target = '_blank';
            link.className = 'file-link';
            link.textContent = file.name || 'Unnamed File';
            nameDiv.appendChild(link);

            const metaDiv = document.createElement('div');
            metaDiv.className = 'file-meta';
            metaDiv.textContent = this.formatFileMeta(file);

            infoDiv.appendChild(nameDiv);
            infoDiv.appendChild(metaDiv);
            li.appendChild(infoDiv);
            this.elements.filesList.appendChild(li);
        });
    }

    formatFileMeta(file) {
        let parts = [];
        const date = file.modifiedTime || file.createdTime;
        if (date) {
            parts.push(`📅 ${new Date(date).toLocaleDateString()}`);
        }
        if (file.mimeType) {
            let type = file.mimeType.split('/').pop().split('.').pop().toUpperCase();
            parts.push(`📁 ${type}`);
        }
        return parts.join(' | ');
    }

    async handleUpload() {
        if (!this.state.activeTab) {
             this.showError("No active tab selected for upload.");
             return;
        }
        const fileInput = this.elements.fileUpload;
        const file = fileInput?.files[0];
        if (!file) {
            this.showError("Please select a file.");
            return;
        }
        this.showFlash("⬆️ Uploading...", "info");
        const formData = new FormData();
        formData.append('file', file);
        try {
            console.log(`⬆️ [UPLOAD] Starting upload for ${file.name} to tab ${this.state.activeTab}`);
            const res = await fetch(`/api/tab/${this.state.activeTab}/upload`, {
                method: 'POST',
                body: formData
            });
            if (!res.ok) {
                const errorText = await res.text();
                throw new Error(`HTTP ${res.status}: ${errorText}`);
            }
            const data = await res.json();
            console.log("✅ [UPLOAD] Success:", data);
            if (data.error) {
                this.showError(data.error);
                return;
            }
            this.showFlash(`✅ Uploaded: ${data.file.name}`, "success");
            if (fileInput) fileInput.value = '';
            this.loadFiles();
        } catch (err) {
            console.error("❌ [UPLOAD] Failed:", err);
            this.showError(`Upload failed: ${err.message}`);
        }
    }

    showFlash(message, category = 'info') {
        if (!this.elements.flashContainer) {
            console.warn("⚠️ [FLASH] Flash container not found in DOM.");
            return;
        }
        const flash = document.createElement('div');
        flash.className = `flash-message ${category}`;
        flash.textContent = message;
        flash.style.opacity = '0';
        flash.style.transform = 'translateX(100%)';
        flash.style.transition = 'opacity 0.3s ease, transform 0.3s ease';

        this.elements.flashContainer.appendChild(flash);

        // Trigger reflow
        // eslint-disable-next-line no-void
        void flash.offsetWidth;

        flash.classList.add('show'); // Add class for transition

        setTimeout(() => {
            flash.classList.remove('show');
            // Remove element after fade-out
            setTimeout(() => {
                if (flash.parentNode) {
                    flash.parentNode.removeChild(flash);
                }
            }, 300);
        }, 3000);
    }

    showError(message) {
        console.error(`🚨 [ERROR] ${message}`);
        this.showFlash(`❌ ${message}`, "error");
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log("🧠 [APP] DOM loaded, initializing OrgPortal...");
    window.APP_CONFIG = window.APP_CONFIG || {};
    new OrgPortal();
});

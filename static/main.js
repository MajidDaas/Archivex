class OrgPortal {
    constructor() {
        this.state = {
            user: null,
            activeTab: null,
            files: [],
            searchQuery: ''
        };

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

        // ✅ AUTO-REDIRECT TO GOOGLE AUTH IF authUrl IS PRESENT AND USER NOT LOGGED IN
        if (window.APP_CONFIG?.authUrl && !this.state?.user) {
            console.log("🚀 [AUTO-REDIRECT] Redirecting to Google Auth...");
            window.location.href = window.APP_CONFIG.authUrl;
        }
    }

    bindEvents() {
        // ✅ FIXED: Redirect to Google Auth URL, NOT to /login
        if (this.elements.loginBtn) {
            this.elements.loginBtn.addEventListener('click', () => {
                console.log("🖱️ [LOGIN BUTTON] Clicked");
                const authUrl = window.APP_CONFIG?.authUrl;

                if (authUrl) {
                    console.log("🔗 [REDIRECT] Going to:", authUrl);
                    window.location.href = authUrl; // ← THIS IS THE FIX
                } else {
                    this.showError("Login URL not available. Please refresh.");
                    console.error("❌ No auth_url found in window.APP_CONFIG");
                }
            });
        }

        if (this.elements.logoutBtn) {
            this.elements.logoutBtn.addEventListener('click', () => {
                fetch('/logout', { method: 'GET' })
                    .then(() => {
                        window.location.href = '/'; // force reload to show login
                    });
            });
        }

        if (this.elements.uploadBtn) {
            this.elements.uploadBtn.addEventListener('click', () => this.handleUpload());
        }

        if (this.elements.searchBtn) {
            this.elements.searchBtn.addEventListener('click', () => this.loadFiles());
        }

        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.loadFiles();
            });
        }
    }

    async checkAuth() {
        try {
            const res = await fetch('/api/user');
            const data = await res.json();

            if (data.authenticated) {
                this.state.user = data;
                this.showMainApp();
                this.loadTabs();
                if (data.accessible_tabs.length > 0) {
                    this.setActiveTab(data.accessible_tabs[0]);
                }
            } else {
                this.showAuthSection();
            }
        } catch (err) {
            console.error("Auth check failed:", err);
            this.showAuthSection();
        }
    }

    showAuthSection() {
        this.elements.authSection.style.display = 'block';
        this.elements.mainApp.style.display = 'none';
    }

    showMainApp() {
        this.elements.authSection.style.display = 'none';
        this.elements.mainApp.style.display = 'block';
        this.elements.userEmail.textContent = `Logged in as: ${this.state.user.email}`;
    }

    async loadTabs() {
        try {
            const res = await fetch('/api/tabs');
            const tabs = await res.json();

            this.elements.tabsContainer.innerHTML = '';
            this.state.user.accessible_tabs.forEach(tabKey => {
                const tabConfig = tabs[tabKey] || { title: tabKey, icon: '' };
                const tabEl = document.createElement('a');
                tabEl.href = '#';
                tabEl.className = 'tab';
                tabEl.innerHTML = `${tabConfig.icon || ''} ${tabConfig.title || tabKey}`;
                tabEl.dataset.tab = tabKey;

                tabEl.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.setActiveTab(tabKey);
                });

                this.elements.tabsContainer.appendChild(tabEl);
            });
        } catch (err) {
            console.error("Failed to load tabs:", err);
        }
    }

    async setActiveTab(tabKey) {
        this.state.activeTab = tabKey;
        this.updateActiveTabUI();
        this.loadFiles();
    }

    async updateActiveTabUI() {
        const res = await fetch('/api/tabs');
        const tabs = await res.json();
        const config = tabs[this.state.activeTab] || {};

        this.elements.tabTitle.textContent = config.title || this.state.activeTab;
        this.elements.tabDescription.textContent = config.description || '';

        // Update active tab class
        document.querySelectorAll('.tab').forEach(el => {
            el.classList.toggle('active', el.dataset.tab === this.state.activeTab);
        });
    }

    async loadFiles() {
        if (!this.state.activeTab) return;

        this.state.searchQuery = this.elements.searchInput.value.trim();
        this.elements.loading.style.display = 'block';
        this.elements.filesList.innerHTML = '';
        this.elements.noFiles.style.display = 'none';

        try {
            const url = `/api/tab/${this.state.activeTab}/files?q=${encodeURIComponent(this.state.searchQuery)}`;
            const res = await fetch(url);
            const data = await res.json();

            if (data.error) {
                this.showError(data.error);
                return;
            }

            this.state.files = data.files || [];
            this.renderFiles();
        } catch (err) {
            this.showError("Failed to load files.");
            console.error(err);
        } finally {
            this.elements.loading.style.display = 'none';
        }
    }

    renderFiles() {
        this.elements.filesList.innerHTML = '';
        if (this.state.files.length === 0) {
            this.elements.noFiles.style.display = 'block';
            return;
        }

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
            link.textContent = file.name;
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
        if (file.modifiedTime) parts.push(`Modified: ${file.modifiedTime.split('T')[0]}`);
        if (file.mimeType) {
            let type = file.mimeType.split('/').pop().split('.').pop();
            parts.push(`Type: ${type}`);
        }
        if (file.size) {
            let sizeKB = (parseInt(file.size) / 1024).toFixed(1);
            parts.push(`Size: ${sizeKB} KB`);
        }
        return parts.join(' | ');
    }

    async handleUpload() {
        const fileInput = this.elements.fileUpload;
        const file = fileInput.files[0];

        if (!file) {
            this.showError("Please select a file.");
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        this.showFlash("Uploading...", "info");

        try {
            const res = await fetch(`/api/tab/${this.state.activeTab}/upload`, {
                method: 'POST',
                body: formData
            });

            const data = await res.json();

            if (data.error) {
                this.showError(data.error);
                return;
            }

            this.showFlash(`✅ Uploaded: ${data.file.name}`, "success");
            fileInput.value = ''; // reset
            this.loadFiles(); // refresh
        } catch (err) {
            this.showError("Upload failed.");
            console.error(err);
        }
    }

    showFlash(message, category = 'info') {
        const flash = document.createElement('div');
        flash.className = `flash-message ${category}`;
        flash.textContent = message;
        flash.style.opacity = '0';
        this.elements.flashContainer.appendChild(flash);

        // Trigger reflow
        void flash.offsetWidth;

        flash.style.opacity = '1';

        setTimeout(() => {
            flash.style.opacity = '0';
            setTimeout(() => {
                if (flash.parentNode) flash.parentNode.removeChild(flash);
            }, 300);
        }, 3000);
    }

    showError(message) {
        this.showFlash(`❌ ${message}`, "error");
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log("🧠 [APP] Initializing OrgPortal...");
    new OrgPortal();
});

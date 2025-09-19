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
            // --- The login button in HTML should trigger this JS, not a Flask route ---
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

        // --- AUTO-REDIRECT TO GOOGLE AUTH ---
        // This relies on `window.APP_CONFIG.authUrl` being set by the Flask template.

    }

    bindEvents() {
        // --- FIXED: Redirect to Google Auth URL ---
        if (this.elements.loginBtn) {
            this.elements.loginBtn.addEventListener('click', (e) => {
                // Prevent default action if the button is inside a form
                e.preventDefault(); 
                console.log("🖱️ [LOGIN BUTTON] Clicked");
                const authUrl = window.APP_CONFIG?.authUrl;

                if (authUrl) {
                    console.log("🔗 [REDIRECT] Going to:", authUrl);
                    window.location.href = authUrl; // ← Redirects to Google
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
                        // Reload the page to show the login section
                        window.location.reload(); 
                    })
                    .catch(err => {
                        console.error("Logout failed:", err);
                        // Even if fetch fails, reload to clear session state if possible
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
                // Load content for the first accessible tab
                if (data.accessible_tabs && data.accessible_tabs.length > 0) {
                    this.setActiveTab(data.accessible_tabs[0]);
                }
            } else {
                this.showAuthSection();
            }
        } catch (err) {
            console.error("❌ [AUTH] Auth check failed:", err);
            this.showAuthSection();
            // Optionally, show a general error message to the user
        }
    }

    showAuthSection() {
        console.log("🏠 [UI] Showing auth section");
        if(this.elements.authSection) this.elements.authSection.style.display = 'block';
        if(this.elements.mainApp) this.elements.mainApp.style.display = 'none';
    }

    showMainApp() {
        console.log("📊 [UI] Showing main app");
        if(this.elements.authSection) this.elements.authSection.style.display = 'none';
        if(this.elements.mainApp) this.elements.mainApp.style.display = 'block';
        if(this.elements.userEmail) this.elements.userEmail.textContent = `Logged in as: ${this.state.user.email}`;
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
                // Use the display name from /api/tabs, fallback to key
                const tabDisplayName = allTabs[tabKey] || tabKey; 
                
                const tabEl = document.createElement('a');
                tabEl.href = '#';
                tabEl.className = 'tab';
                // Assuming /api/tabs returns a simple string name
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
        if (this.state.activeTab === tabKey) return; // Avoid redundant load
        console.log(`📌 [TABS] Setting active tab to: ${tabKey}`);
        this.state.activeTab = tabKey;
        this.updateActiveTabUI();
        this.loadFiles(); // Load files for the new active tab
    }

    async updateActiveTabUI() {
        if (!this.state.activeTab) return;
        
        try {
            const res = await fetch('/api/tabs');
            const allTabs = await res.json();
            // Get the display name for the active tab
            const activeTabDisplayName = allTabs[this.state.activeTab] || this.state.activeTab;

            if(this.elements.tabTitle) this.elements.tabTitle.textContent = activeTabDisplayName;
            // If you add descriptions to your TABS config, use them here
            // if(this.elements.tabDescription) this.elements.tabDescription.textContent = config.description || '';
            
            // Update active tab class in the UI
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

        // Get search query from input
        this.state.searchQuery = this.elements.searchInput ? this.elements.searchInput.value.trim() : '';

        // Show loading indicator
        if(this.elements.loading) this.elements.loading.style.display = 'block';
        if(this.elements.filesList) this.elements.filesList.innerHTML = '';
        if(this.elements.noFiles) this.elements.noFiles.style.display = 'none';

        try {
            console.log(`🗂️ [FILES] Loading files for tab: ${this.state.activeTab}, search: '${this.state.searchQuery}'`);
            // Build API URL
            let url = `/api/tab/${this.state.activeTab}/files`;
            if (this.state.searchQuery) {
                url += `?q=${encodeURIComponent(this.state.searchQuery)}`;
            }
            
            const res = await fetch(url);
            
            // Check for non-OK HTTP responses
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
            // Hide loading indicator
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
        // Use createdTime if modifiedTime isn't available
        const date = file.modifiedTime || file.createdTime; 
        if (date) {
            parts.push(`Date: ${new Date(date).toLocaleDateString()}`);
        }
        if (file.mimeType) {
            // Simple extraction of type
            let type = file.mimeType.split('/').pop().split('.').pop().toUpperCase();
            parts.push(`Type: ${type}`);
        }
        // Drive API v3 `files.list` doesn't return size by default.
        // You need to add 'size' to the 'fields' parameter.
        // For now, we'll skip size if not present.
        // if (file.size) {
        //     let sizeKB = (parseInt(file.size, 10) / 1024).toFixed(1);
        //     parts.push(`Size: ${sizeKB} KB`);
        // }
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

        this.showFlash("Uploading...", "info");

        const formData = new FormData();
        formData.append('file', file);

        try {
            console.log(`⬆️ [UPLOAD] Starting upload for ${file.name} to tab ${this.state.activeTab}`);
            const res = await fetch(`/api/tab/${this.state.activeTab}/upload`, {
                method: 'POST',
                body: formData
            });

            // Check for non-OK HTTP responses
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
            if (fileInput) fileInput.value = ''; // reset the file input
            this.loadFiles(); // refresh the file list
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
        // Initial state for animation
        flash.style.opacity = '0'; 
        flash.style.transition = 'opacity 0.3s ease-in-out';
        this.elements.flashContainer.appendChild(flash);

        // Trigger reflow to ensure the initial state is applied before transition
        // eslint-disable-next-line no-void
        void flash.offsetWidth; 

        flash.style.opacity = '1';

        setTimeout(() => {
            flash.style.opacity = '0';
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

// --- Initialize the application when the DOM is fully loaded ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("🧠 [APP] DOM loaded, initializing OrgPortal...");
    // Ensure APP_CONFIG is defined
    window.APP_CONFIG = window.APP_CONFIG || {};
    new OrgPortal();
});


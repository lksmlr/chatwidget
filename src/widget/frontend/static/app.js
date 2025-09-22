/**
 * Kiwi Chat Widget
 * Main application entry point - Shadow DOM Compatible
 *
 * This file imports all the modular components of the Kiwi Chat Widget.
 */

// Global widget container for Shadow DOM isolation
class KiwiChatWidget {
    constructor(shadowRoot, baseUrl) {
        this.shadowRoot = shadowRoot;
        this.baseUrl = baseUrl;
        this.loadedScripts = new Set();
    }

    // Helper function to load scripts sequentially within Shadow DOM context
    loadScript(src, callback) {
        if (this.loadedScripts.has(src)) {
            callback();
            return;
        }

        const script = document.createElement('script');
        script.src = `${this.baseUrl}/static/modules/${src}`;
        script.onload = () => {
            this.loadedScripts.add(src);
            callback();
        };
        script.onerror = () => console.error(`Failed to load script: ${src}`);
        document.head.appendChild(script);
    }

    // Initialize widget with Shadow DOM context
    async init() {
        // Set global context for modules
        window.KIWI_WIDGET_CONTEXT = {
            shadowRoot: this.shadowRoot,
            baseUrl: this.baseUrl,
            querySelector: (selector) => this.shadowRoot.querySelector(selector),
            querySelectorAll: (selector) => this.shadowRoot.querySelectorAll(selector),
            getElementById: (id) => this.shadowRoot.getElementById(id)
        };

        const scripts = [
            'kiwi-config.js',
            'kiwi-thread.js',
            'kiwi-chat.js',
            'kiwi-ui.js',
            'kiwi-collections.js',
            'kiwi-app.js'
        ];

        return new Promise((resolve) => {
            this.loadNextScript(0, scripts, resolve);
        });
    }

    loadNextScript(index, scripts, resolve) {
        if (index < scripts.length) {
            this.loadScript(scripts[index], () => this.loadNextScript(index + 1, scripts, resolve));
        } else {
            resolve();
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeWidget);
} else {
    initializeWidget();
}

function initializeWidget() {
    // Check if we're in Shadow DOM context or need to create it
    if (window.KIWI_SHADOW_ROOT && window.BASE_URL) {
        const widget = new KiwiChatWidget(window.KIWI_SHADOW_ROOT, window.BASE_URL);
        widget.init();
    }
}

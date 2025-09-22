(function() {
    // Initialize widget when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidget);
    } else {
        initWidget();
    }

    async function initWidget() {
        try {
            const currentScript = document.currentScript || document.querySelector('script[src*="embed.js"]');
            const baseUrl = new URL(currentScript.src).origin;

            // Create widget container with Shadow DOM
            const container = document.createElement('div');
            container.id = 'kiwi-chat-widget-container';
            container.style.cssText = 'position:fixed;bottom:0;right:0;width:100%;height:100%;z-index:9999;pointer-events:none;';

            const shadowRoot = container.attachShadow({ mode: 'closed' });

            // Set up global context
            window.BASE_URL = baseUrl;
            window.KIWI_SHADOW_ROOT = shadowRoot;
            window.KIWI_WIDGET_CONTEXT = {
                shadowRoot,
                baseUrl,
                querySelector: sel => shadowRoot.querySelector(sel),
                querySelectorAll: sel => shadowRoot.querySelectorAll(sel),
                getElementById: id => shadowRoot.getElementById(id)
            };

            // Load styles, HTML, and scripts
            await Promise.all([
                loadStyles(shadowRoot, baseUrl),
                loadHtml(shadowRoot, baseUrl)
            ]);

            // Add to document
            document.body.appendChild(container);

            // Create scripts container
            const scriptsContainer = document.createElement('div');
            scriptsContainer.style.display = 'none';
            shadowRoot.appendChild(scriptsContainer);

            // Load libraries and modules
            await loadExternalLibraries(scriptsContainer);
            await loadWidgetModules(baseUrl, scriptsContainer);

            console.log('Kiwi Chat Widget loaded successfully');
        } catch (error) {
            console.error('Failed to initialize Kiwi Chat Widget:', error);
        }
    }

    async function loadStyles(shadowRoot, baseUrl) {
        // Base styles for isolation
        const baseStyle = document.createElement('style');
        baseStyle.textContent = `
            :host { all:initial; display:block; contain:layout style paint; }
            * { pointer-events:auto; }
        `;
        shadowRoot.appendChild(baseStyle);

        // Load all CSS files
        const stylesheets = [
            'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@48,300,0,0',
            'https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,300..800;1,300..800&family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap',
            'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/default.min.css',
            'https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/katex.min.css',
            `${baseUrl}/static/style.final.css`
        ];

        await Promise.all(stylesheets.map(async href => {
            try {
                const response = await fetch(href);
                const cssText = await response.text();

                // Fix relative URLs in CSS
                const fixedCss = cssText.replace(/url\(['"]?([^'")]+)['"]?\)/g, (match, url) => {
                    if (url.startsWith('data:') || url.startsWith('http') || url.startsWith('//')) {
                        return match;
                    }
                    return `url("${new URL(href).origin}/${url.replace(/^\//, '')}")`;
                });

                const style = document.createElement('style');
                style.textContent = fixedCss;
                shadowRoot.appendChild(style);
            } catch (e) {
                console.warn(`Failed to load stylesheet: ${href}`, e);
            }
        }));

        // Also load Material Icons in main document for compatibility
        if (!document.querySelector('link[href*="Material+Symbols+Outlined"]')) {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@48,300,0,0';
            document.head.appendChild(link);
        }
    }

    async function loadHtml(shadowRoot, baseUrl) {
        const response = await fetch(`${baseUrl}/`);
        const htmlText = await response.text();

        const contentDiv = document.createElement('div');
        contentDiv.innerHTML = new DOMParser()
            .parseFromString(htmlText, 'text/html')
            .body.innerHTML;

        shadowRoot.appendChild(contentDiv);
    }

    async function loadExternalLibraries(container) {
        // Define libraries with dependencies
        const libraries = [
            { url: 'https://cdn.jsdelivr.net/npm/marked/marked.min.js', name: 'marked', required: true },
            { url: 'https://cdn.jsdelivr.net/npm/dompurify@2.4.0/dist/purify.min.js', name: 'DOMPurify', required: true },
            { url: 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js', name: 'hljs', required: false, timeout: 10000 },
            { url: 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/latex.min.js', name: 'hljs_latex', depends: 'hljs', required: false },
            { url: 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/go.min.js', name: 'hljs_go', depends: 'hljs', required: false },
            { url: 'https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/katex.min.js', name: 'katex', required: false, timeout: 10000 },
            { url: 'https://cdn.jsdelivr.net/npm/katex@0.16.22/dist/contrib/auto-render.min.js', name: 'renderMathInElement', depends: 'katex', required: false },
            { url: 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js', name: 'html2canvas', required: false },
            { url: 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js', name: 'MathJax', required: false, timeout: 15000 }
        ];

        // Store library references
        window.KIWI_LIBS = {};

        // Load libraries sequentially to respect dependencies
        for (const lib of libraries) {
            try {
                // Skip if dependency not met
                if (lib.depends && !window.KIWI_LIBS[lib.depends]) {
                    console.warn(`Skipping ${lib.name} as dependency ${lib.depends} is not available`);
                    continue;
                }

                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = lib.url;
                    script.crossOrigin = 'anonymous';

                    const timeoutId = setTimeout(() => {
                        if (lib.required) {
                            reject(new Error(`Timeout loading ${lib.name}`));
                        } else {
                            console.warn(`Timeout loading ${lib.name}, continuing...`);
                            resolve();
                        }
                    }, lib.timeout || 8000);

                    script.onload = () => {
                        clearTimeout(timeoutId);

                        // Store library reference
                        const libName = lib.name.split('_')[0]; // Handle hljs_latex etc.
                        if (window[libName]) {
                            window.KIWI_LIBS[libName] = window[libName];
                        }

                        resolve();
                    };

                    script.onerror = (error) => {
                        clearTimeout(timeoutId);
                        if (lib.required) {
                            reject(new Error(`Required library ${lib.name} failed to load`));
                        } else {
                            console.warn(`Optional library ${lib.name} failed to load`);
                            resolve();
                        }
                    };

                    container.appendChild(script);
                });

            } catch (error) {
                if (lib.required) throw error;
                console.warn(`Non-critical error loading ${lib.name}:`, error);
            }
        }

        // Make libraries available to widget context
        Object.assign(window.KIWI_WIDGET_CONTEXT, window.KIWI_LIBS);
    }

    async function loadWidgetModules(baseUrl, container) {
        const modules = [
            'kiwi-config.js',
            'kiwi-thread.js',
            'kiwi-chat.js',
            'kiwi-ui.js',
            'kiwi-collections.js',
            'kiwi-app.js'
        ];

        // Load modules sequentially
        for (const module of modules) {
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = `${baseUrl}/static/modules/${module}`;

                const timeoutId = setTimeout(() => {
                    reject(new Error(`Timeout loading module ${module}`));
                }, 10000);

                script.onload = () => {
                    clearTimeout(timeoutId);
                    resolve();
                };

                script.onerror = () => {
                    clearTimeout(timeoutId);
                    reject(new Error(`Module ${module} failed to load`));
                };

                container.appendChild(script);
            });
        }

        // Initialize app
        setTimeout(() => {
            if (typeof initApp === 'function') {
                try {
                    initApp();
                } catch (error) {
                    console.error('Error initializing app:', error);
                }
            } else {
                console.error('initApp function not found');
            }
        }, 100);
    }
})();
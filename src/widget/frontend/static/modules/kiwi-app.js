/**
 * Kiwi App
 * Main application file that initializes all components
 */

/**
 * Initializes the application
 */
async function initApp() {
    // Initialize collections
    await addCollectionsToDropdown();
    await setUpWidgetFrontend(collection);

    // Set up thread ID
    let thread_id = getThreadID();

    // If the thread_id is not set, generate a new one and set it in local storage
    // Only fetch the chat history if the thread_id was already set, because otherwise the chat history doesn't exist in MongoDB
    if (!thread_id) {
        thread_id = generateThreadId();
        setThreadID(thread_id);
    } else {
        await buildChat(thread_id);
    }

    // Blinking widget toggler animation
    widgetToggler.classList.add("highlight");
    let interval = setInterval(function () {
        widgetToggler.classList.toggle("grow");
        widgetToggler.classList.toggle("shrink");
    }, 500);

    setTimeout(function () {
        clearInterval(interval);
        widgetToggler.classList.remove("highlight");
        widgetToggler.classList.remove("grow");
        widgetToggler.classList.remove("shrink");
    }, 5000);

    // Set up event listeners
    setupEventListeners();
}

/**
 * Sets up all event listeners
 */
function setupEventListeners() {
    // Chat scrolling
    chatbox.scrollTop = chatbox.scrollHeight;

    // Send button
    sendButton.addEventListener("click", (event) => {
        event.preventDefault();
        if (isProcessing) return;
        (async () => {
            isProcessing = true;
            await handleSendMessage(chatLine.value.trim(), uploadedFile);
            chatbox.scrollTop = chatbox.scrollHeight;
            isProcessing = false;
        })();
    });

    // Enter key handling - use Shadow DOM safe event listener
    const handleKeyDown = (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            if (isProcessing) return;
            (async () => {
                isProcessing = true;
                await handleSendMessage(chatLine.value.trim(), uploadedFile);
                isProcessing = false;
            })();
        }
    };
    
    if (getContext().shadowRoot !== document) {
        getContext().shadowRoot.addEventListener("keydown", handleKeyDown);
    } else {
        document.addEventListener("keydown", handleKeyDown);
    }

    // Toggle widget
    widgetToggler.addEventListener('click', () => {
        chatWidget.classList.toggle('hidden');
        widgetToggler.classList.toggle('toggled');
    });

    // Dynamic input textfield height - use Shadow DOM safe event listener
    const handleInput = () => {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
        chatInput.style.height = 'auto';
    };
    
    if (getContext().shadowRoot !== document) {
        getContext().shadowRoot.addEventListener('input', handleInput);
    } else {
        document.addEventListener('input', handleInput);
    }

    // File upload
    fileUpload.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        uploadedFile = fileInput.files.item(0);
        createPreview(uploadedFile);
        fileInput.value = '';
    });

    // Drag and Drop functionality
    const dropZone = chatWidget;

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
        document.body.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            const file = files[0];

            // Check if file type is allowed
            const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/svg+xml', 'application/pdf', 'text/plain', 'text/csv'];

            if (file.type && allowedTypes.includes(file.type)) {
                uploadedFile = file;
                createPreview(file);
            } else if (file.type.startsWith('image/')) {
                // Allow any image type
                uploadedFile = file;
                createPreview(file);
            } else {
                alert('Dateityp nicht unterstützt. Erlaubte Formate: Bilder, PDF, TXT, CSV');
            }
        }
    }, false);

    // Paste functionality - only in textarea
    chatLine.addEventListener('paste', (e) => {
        const items = e.clipboardData.items;

        for (let i = 0; i < items.length; i++) {
            const item = items[i];

            // Check if it's a file
            if (item.kind === 'file') {
                const file = item.getAsFile();

                // Check if file type is allowed
                const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/svg+xml', 'application/pdf', 'text/plain', 'text/csv'];

                if (file && file.type && allowedTypes.includes(file.type)) {
                    e.preventDefault();
                    uploadedFile = file;
                    createPreview(file);
                    break;
                } else if (file && file.type.startsWith('image/')) {
                    // Allow any image type
                    e.preventDefault();
                    uploadedFile = file;
                    createPreview(file);
                    break;
                }
            }
        }
    });

    // Web search
    websearchButton.addEventListener('click', () => {
        if (websearchButton.style.color !== "blue") {
            websearchButton.style.color = "blue";
        } else {
            websearchButton.style.color = "#C72426";
        }
    });

    // Resize widget
    resizeHandles.forEach(resizeHandle => {
        resizeHandle.addEventListener('mousedown', (e) => {
            activeHandle = resizeHandle;
            initResize(e);
        });

        resizeHandle.addEventListener('touchstart', (e) => {
            activeHandle = resizeHandle;
            initResize(e);
        }, { passive: false });
    });

    // Clear button
    clearButton.addEventListener("click", function () {
        let thread_id = getThreadID();
        deleteChat(thread_id);
    });

    // Menu button
    menuButton.addEventListener("click", toggleDropdown);

    // Dropdown selected
    selected.addEventListener("click", () => {
        optionsContainer.classList.toggle("hidden");
    });

    // Dropdown options - use Shadow DOM safe selector
    getContext().querySelectorAll(".dropdown-option").forEach(option => {
        option.addEventListener("click", () => {
            selected.textContent = option.textContent;
            optionsContainer.classList.add("hidden");
            changeDropdownValue(option.dataset.value);
        });
    });

    // Key submit
    keySubmit.addEventListener("click", async function () {
        await processKey(keyInput.value);
    });

    // Info button
    if (infoButton) {
        infoButton.addEventListener('click', () => {
            infoButton.classList.toggle('active');
        });

        const handleInfoButtonClick = (e) => {
            if (!infoButton.contains(e.target)) {
                infoButton.classList.remove('active');
            }
        };
        
        if (getContext().shadowRoot !== document) {
            getContext().shadowRoot.addEventListener('click', handleInfoButtonClick);
        } else {
            document.addEventListener('click', handleInfoButtonClick);
        }
    }
}

function onWidgetToggle(isOpen) {
    if (isOpen) {
        window.parent.postMessage('widget-opened', '*');
    } else {
        window.parent.postMessage('widget-closed', '*');
    }
}

// Initialize the app when the DOM is fully loaded
window.addEventListener("load", function () {
    initApp();
});
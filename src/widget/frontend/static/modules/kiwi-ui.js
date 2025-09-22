/**
 * Kiwi UI Module
 * Handles UI interactions, widget resizing, and file previews
 */

// Resize variables
let activeHandle = null;
let initialMouseX, initialMouseY, startWidth, startHeight;

/**
 * Toggles the dropdown menu
 */
function toggleDropdown() {
    if (dropdownMenu.style.display === "none" || dropdownMenu.style.display === "") {
        dropdownMenu.style.display = "flex";
        dropdownMenu.style.opacity = "1";
        menuList.style.pointerEvents = "auto";
        if (optionsContainer.classList.contains("hidden")) {
            optionsContainer.classList.remove("hidden");
        }
    } else {
        dropdownMenu.style.display = "none";
        dropdownMenu.style.opacity = "0";
        menuList.style.pointerEvents = "none";
        if (!optionsContainer.classList.contains("hidden")) {
            optionsContainer.classList.add("hidden");
        }
        selected.textContent = "Select ...";
        keyInputWrapper.setAttribute("hidden", true);
        collection = "Basiswissen";
        deleteChatFrontend();
        let thread_id = getThreadID();
        buildChat(thread_id);
        setUpWidgetFrontend(collection);
    }
}

/**
 * Initializes resize operation
 * @param {Event} e - Mouse or touch event
 */
function initResize(e) {
    e.preventDefault();

    let clientX, clientY;

    if (e.type === "touchstart") {
        clientX = e.touches[0].clientX;
        clientY = e.touches[0].clientY;
    } else {
        clientX = e.clientX;
        clientY = e.clientY;
    }

    initialMouseX = clientX;
    initialMouseY = clientY;

    const widget = chatWidget.getBoundingClientRect();
    startWidth = widget.width;
    startHeight = widget.height;

    window.addEventListener('mousemove', resize, false);
    window.addEventListener('mouseup', stopResize, false);

    window.addEventListener('touchmove', onTouchResize, { passive: false });
    window.addEventListener('touchend', stopResize, false);
}

/**
 * Mouse resize handler
 * @param {MouseEvent} e - Mouse event
 */
function resize(e) {
    handleResize(e.clientX, e.clientY);
}

/**
 * Touch resize handler
 * @param {TouchEvent} e - Touch event
 */
function onTouchResize(e) {
    e.preventDefault();
    handleResize(e.touches[0].clientX, e.touches[0].clientY);
}

/**
 * Handles the resize calculations
 * @param {number} currentX - Current X position
 * @param {number} currentY - Current Y position
 */
function handleResize(currentX, currentY) {
    if (!activeHandle) return;

    if (activeHandle.classList.contains("top-left")) {
        chatWidget.style.width = `${startWidth + initialMouseX - currentX}px`;
        chatWidget.style.height = `${startHeight + initialMouseY - currentY}px`;
    } else if (activeHandle.classList.contains("top")) {
        chatWidget.style.height = `${startHeight + initialMouseY - currentY}px`;
    } else if (activeHandle.classList.contains("left")) {
        chatWidget.style.width = `${startWidth + initialMouseX - currentX}px`;
    }
}

/**
 * Stops the resize operation
 */
function stopResize() {
    window.removeEventListener('mousemove', resize, false);
    window.removeEventListener('mouseup', stopResize, false);

    window.removeEventListener('touchmove', onTouchResize, false);
    window.removeEventListener('touchend', stopResize, false);
    activeHandle = null;
}

/**
 * Creates a preview for uploaded files
 * @param {File} file - File to preview
 */
function createPreview(file) {
    previewContainer.innerHTML = '';

    const preview = document.createElement('div');
    preview.classList.add('preview');

    const removeButton = document.createElement('span');
    removeButton.classList.add('remove-button', 'material-symbols-outlined');
    removeButton.textContent = 'close';
    removeButton.addEventListener('click', () => {
        uploadedFile = null;
        preview.remove();
    });

    if (file.type.startsWith('image/')) {
        const image = document.createElement('img');
        image.classList.add('preview-image');
        image.src = URL.createObjectURL(file);
        preview.appendChild(image);
    } else {
        const text = document.createElement('span');
        text.classList.add('file-name');
        text.textContent = file.name;
        preview.appendChild(text);
    }
    
    preview.appendChild(removeButton);
    previewContainer.appendChild(preview);
    textarea.scrollTop = textarea.scrollHeight;
}

/**
 * Checks if an option with a specific value exists in the dropdown
 * @param {HTMLElement} dropdownContainer - The dropdown container
 * @param {string} valueToCheck - The value to check for
 * @returns {boolean} True if option exists, false otherwise
 */
function isOptionExists(dropdownContainer, valueToCheck) {
    const options = dropdownContainer.querySelectorAll(".dropdown-option");

    for (let option of options) {
        if (option.dataset.value === valueToCheck) {
            return true;
        }
    }

    return false;
}

/**
 * Changes the selected collection in the dropdown
 * @param {string} newvalue - New collection value
 */
function changeDropdownValue(newvalue) {
    if (newvalue !== "key") {
        // Delete all messages in the frontend, chat history still available in the backend
        deleteChatFrontend();

        // Set current collection to new value
        collection = newvalue;

        // Get the thread_id for the new collection
        let thread_id = getThreadID();

        if (!thread_id) {
            thread_id = generateThreadId();
            setThreadID(thread_id);
        } else {
            buildChat(thread_id);
        }

        keyInputWrapper.setAttribute("hidden", true);
        setUpWidgetFrontend(collection);
    } else {
        keyInputWrapper.removeAttribute("hidden");
    }
}

/**
 * Deletes an optional collection from the dropdown
 * @param {string} value - Collection value to delete
 */
function deleteOptionalCollection(value) {
    const dropdownOptions = getContext().getElementById("dropdownOptions");
    const optionToRemove = dropdownOptions.querySelector(`.dropdown-option[data-value="${value}"]`);

    if (optionToRemove) {
        optionToRemove.remove();
    }

    if (collection == value) {
        selected.textContent = "Select ...";
        collection = "Basiswissen";

        // Get the thread_id for the new collection
        let thread_id = getThreadID();

        if (!thread_id) {
            thread_id = generateThreadId();
            setThreadID(thread_id);
        } else {
            buildChat(thread_id);
        }

        setUpWidgetFrontend(collection);
    }
}
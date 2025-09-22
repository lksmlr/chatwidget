/**
 * Kiwi Collections Module
 * Handles collection management and API communication
 */

/**
 * Loads collections from MongoDB
 * @returns {Promise<Array>} Promise that resolves with collections array
 */
async function loadCollectionsFromMongoDB() {
    try {
        const response = await fetch(`${domain}/get_collections`);
        return await response.json();
    } catch (error) {
        console.error('Fehler beim Abrufen der Collections:', error);
        return [];
    }
}

/**
 * Removes text after the last underscore in a string
 * @param {string} str - Input string
 * @returns {string} String with part after last underscore removed
 */
function cutAfterLastUnderscore(str) {
    const lastIndex = str.lastIndexOf('_');
    if (lastIndex === -1) {
        return str;
    }
    return str.substring(0, lastIndex);
}

/**
 * Adds collections to dropdown menu
 */
async function addCollectionsToDropdown() {
    const collections = await loadCollectionsFromMongoDB();
    const dropdownOptions = getContext().getElementById('dropdownOptions');

    collections.forEach(inst => {
        if(inst.password_required !== true) {
                const option = document.createElement('div');
                option.classList.add('dropdown-option');
                option.setAttribute('data-value', inst.collection_name);

                // Text label in separate <span>
                const label = document.createElement('span');
                label.classList.add('option-label');
                label.textContent = inst.data_source_name;

                option.appendChild(label);
                dropdownOptions.appendChild(option);
        }
    });
}

/**
 * Loads users from MongoDB
 * @returns {Promise<Array>} Promise that resolves with users array
 */
async function loadUsersFromMongoDB() {
    try {
        const response = await fetch(`${domain}/get_users`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Fehler beim Abrufen der User:', error);
        return [];
    }
}

/**
 * Sets the bot name based on user
 * @param {string} nameOfUser - Username
 */
async function setUserBotName(nameOfUser) {
    const users = await loadUsersFromMongoDB();

    users.forEach(user => {
        if(user.username === nameOfUser) {
            chatBotName.textContent = user.bot_name;
        }
    });
}

/**
 * Sets up the widget frontend based on collection
 * @param {string} collection - Collection name
 */
async function setUpWidgetFrontend(collection) {
    const collections = await loadCollectionsFromMongoDB();

    let bot_name = "";
    collections.forEach(inst => {
        if(inst.collection_name === collection) {
            welcomeMessage.innerHTML = inst.welcome_message;
            dropdownMenu.value = collection;
            bot_name = inst.bot_name;
        }
    });
    
    if (bot_name) {
        selectedCollection.innerHTML = bot_name;
        menuButton.style.color = "blue";
    } else {
        collection = "Basiswissen";
        selectedCollection.innerHTML = collection;
        welcomeMessage.innerHTML = "Hallo ich bin ein Chatbot. Wie kann ich helfen?";
        menuButton.style.color = "#C72426";
    }
}

/**
 * Processes a collection key
 * @param {string} key - Collection key
 */
async function processKey(key) {
    const dropdownOptions = getContext().getElementById('dropdownOptions');

    if (!key) {
        keyInput.value = "";
        keyInput.placeholder = "Please insert Key!";
        return;
    }

    try {
        const response = await fetch(`${domain}/process_key`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ key: key })
        });

        const data = await response.json();

        if (response.ok) {
            if (data.answer === "collection found" && !isOptionExists(dropdownOptions, data.collection_name)) {
                const option = document.createElement('div');
                option.classList.add('dropdown-option');
                option.setAttribute('data-value', data.collection_name);

                // Text label in separate <span>
                const label = document.createElement('span');
                label.classList.add('option-label');
                label.textContent = data.data_source_name;

                const deleteIcon = document.createElement('span');
                deleteIcon.classList.add('material-symbols-outlined', 'delete-icon');
                deleteIcon.textContent = 'playlist_remove';

                // Click behavior
                option.addEventListener("click", () => {
                    getContext().getElementById('dropdownSelected').textContent = label.textContent;
                    dropdownOptions.classList.add("hidden");
                    changeDropdownValue(data.collection_name);
                });

                deleteIcon.addEventListener("click", (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    deleteOptionalCollection(data.collection_name);
                });

                option.appendChild(label);
                option.appendChild(deleteIcon);
                dropdownOptions.appendChild(option);

                keyInput.value = "";
                keyInput.placeholder = "Collection added!";
            } else if (isOptionExists(dropdownOptions, data.collection_name)) {
                keyInput.value = "";
                keyInput.placeholder = "Key already used!";
            } else {
                keyInput.value = "";
                keyInput.placeholder = "Wrong Key!";
            }
        } else {
            console.error("Error fetching the answer");
        }
    } catch (error) {
        console.error("Error while processing the key:", error);
    }
}
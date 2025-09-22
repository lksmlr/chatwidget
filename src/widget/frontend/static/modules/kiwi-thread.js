/**
 * Kiwi Thread Module
 * Handles thread ID management for persistent conversations
 */

/**
 * Generates a new thread ID
 * @returns {string} New thread ID
 */
function generateThreadId() {
    return "thread_" + Math.random().toString(36).substr(2, 9);
}

/**
 * Gets the thread ID for the current collection
 * @returns {string|boolean} Thread ID if exists and valid, false otherwise
 */
function getThreadID() {
    // Read out local storage
    const local_storage = JSON.parse(localStorage.getItem("chathistory") || "{}");
    const local_storage_collection = local_storage[collection];

    // Create a timestamp for 7 days ago for checking if the thread_id is older than 7 days
    const now = Date.now();
    const sevenDaysAgo = now - 7 * 24 * 60 * 60 * 1000;

    // Check if the collection exists and if the created_at timestamp is newer than 7 days
    // else return false
    if (local_storage_collection && local_storage_collection.created_at > sevenDaysAgo) {
        return local_storage_collection.thread_id;
    } else {
        return false;
    }
}

/**
 * Sets the thread ID in local storage
 * @param {string} thread_id - Thread ID to store
 */
function setThreadID(thread_id) {
    let local_storage = localStorage.getItem("chathistory");

    // Check if chathistory in local storage already exists
    if (!local_storage) {
        local_storage = {};
    } else {
        local_storage = JSON.parse(local_storage);
    }

    // Enter new thread_id with timestamp in the current selected collection
    local_storage[collection] = { thread_id: thread_id, created_at: Date.now() };

    // Write in the local storage
    localStorage.setItem("chathistory", JSON.stringify(local_storage));
}

/**
 * Deletes the thread ID for the current collection
 */
function deleteThreadID() {
    let local_storage = localStorage.getItem("chathistory");

    if (!local_storage) {
        return;
    }

    // Parse the local storage data
    local_storage = JSON.parse(local_storage);

    // Delete the specified collection
    delete local_storage[collection];

    // Write the updated data back to local storage
    localStorage.setItem("chathistory", JSON.stringify(local_storage));
}
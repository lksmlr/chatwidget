// Use window-scoped variables defined in the HTML template
let currentChunks = [];
let filteredChunks = [];
let selectedChunkIndex = 0;
let isSearchActive = false;

// Make sure chunksVars exists and has required properties
if (!window.chunksVars) {
    console.error("chunksVars not defined. This could cause problems.");
    window.chunksVars = {
        collectionId: '',
        filename: '',
        fileIconUrl: '',
        saveIconUrl: ''
    };
}

// Load chunks when the page loads
document.addEventListener('DOMContentLoaded', () => {
    switchToView();
    
    // Add search input event listener
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.trim();
            searchChunks(searchTerm);
        });
    }
    
    setTimeout(() => {
        loadChunks();
    }, 500);
});

// Function to load chunks for the file
function loadChunks() {
    try {
        // Handle the filename, which might be a URL itself
        let rawFilename;

        // If we have fileMap data, prefer using that
        if (window.chunksVars.fileMap && typeof window.chunksVars.fileMap.name === 'string') {
            rawFilename = window.chunksVars.fileMap.name;
        } else {
            // Fallback to direct filename
            rawFilename = typeof window.chunksVars.filename === 'string' ? 
                window.chunksVars.filename : 
                String(window.chunksVars.filename);
        }
        
        // Special handling for filenames that are URLs
        // Convert to a safe format for API calls
        const isUrl = rawFilename.startsWith('http://') || rawFilename.startsWith('https://');
        
        let encodedFilename;
        if (isUrl) {
            // For URLs, replace each / with %2F before the default encoding
            const safeFilename = rawFilename.replace(/\//g, '%2F');
            encodedFilename = encodeURIComponent(safeFilename);
        } else {
            // For regular filenames, just encode normally
            encodedFilename = encodeURIComponent(rawFilename);
        }
        
        const endpoint = `/admin/points/${window.chunksVars.collectionId}/${encodedFilename}`;
        
        // Show explicit loading message
        document.getElementById('chunks-list').innerHTML = '<div class="loading-message">Loading chunks from API...</div>';
        
        fetch(endpoint)
            .then(response => {
                if (!response.ok) {
                    console.error("Response not OK. Status:", response.status);
                    throw new Error(`Failed to load chunks: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (!Array.isArray(data)) {
                    console.error("Expected array but got:", typeof data);
                    document.getElementById('chunks-list').innerHTML = 
                        '<div class="error-message">Error: Received unexpected data format</div>';
                    return;
                }
                
                currentChunks = data;
                
                displayChunksList();
                
                if (currentChunks.length > 0) {
                    selectChunk(0); // Select the first chunk by default
                } else {
                    // If there are no chunks for this file, redirect back to the dashboard
                    window.location.href = '/dashboard/';
                }
            })
            .catch(error => {
                console.error('Error loading chunks:', error);
                document.getElementById('chunks-list').innerHTML = 
                    `<div class="error-message">Error loading chunks: ${error.message}</div>`;
            });
    } catch (e) {
        console.error("Exception in loadChunks function:", e);
        document.getElementById('chunks-list').innerHTML = 
            `<div class="error-message">Error in loadChunks function: ${e.message}</div>`;
    }
}

// Function to display the list of chunks
function displayChunksList() {
    const chunksList = document.getElementById('chunks-list');
    chunksList.innerHTML = '';
    
    // Use filtered chunks if search is active, otherwise use all chunks
    const chunksToDisplay = isSearchActive ? filteredChunks : currentChunks.map((chunk, index) => ({ chunk, originalIndex: index }));
    
    chunksToDisplay.forEach((chunkData, displayIndex) => {
        const chunk = chunkData.chunk;
        const originalIndex = chunkData.originalIndex;
        
        // Check if chunk has the expected structure
        if (!chunk || typeof chunk.text !== 'string') {
            console.error(`Chunk ${displayIndex} has invalid structure:`, chunk);
            return;
        }
        
        const chunkItem = document.createElement('div');
        chunkItem.className = 'chunk-item';
        chunkItem.dataset.index = originalIndex; // Use original index for selection
        chunkItem.dataset.hasValidId = 'true';
        
        // Create icon element
        const iconElement = document.createElement('span');
        iconElement.className = 'chunk-icon';
        iconElement.innerHTML = `<img src="${window.chunksVars.fileIconUrl}" alt="Chunk">`;
        
        // Create chunk title
        const titleElement = document.createElement('span');
        titleElement.className = 'chunk-title';
        titleElement.textContent = `Chunk ${originalIndex + 1}`;
        
        // Add preview text if available
        let previewSourceText = '';
        try {
            const text = typeof chunk.text === 'string' ? chunk.text : '';
            // Capture everything after a line that starts with "Content:" (case-insensitive)
            const match = text.match(/(?:^|\n)Content:\s*([\s\S]*)$/i);
            if (match && match[1]) {
                previewSourceText = match[1].trim();
            } else {
                // Fallbacks: try skipping the first line if it looks like a "Source:" header
                const lines = text.split('\n');
                if (lines.length > 1 && /^\s*Source\s*:/i.test(lines[0])) {
                    previewSourceText = lines.slice(1).join('\n').trim();
                } else {
                    previewSourceText = text.trim();
                }
            }
        } catch (e) {
            previewSourceText = '';
        }

        const previewText = previewSourceText.length > 30
            ? previewSourceText.substring(0, 30) + '...'
            : previewSourceText;
        
        const previewElement = document.createElement('div');
        previewElement.className = 'chunk-preview';
        previewElement.textContent = previewText;
        
        // Add elements to chunk item
        chunkItem.appendChild(iconElement);
        
        const textContainer = document.createElement('div');
        textContainer.className = 'chunk-text-container';
        textContainer.appendChild(titleElement);
        textContainer.appendChild(previewElement);
        chunkItem.appendChild(textContainer);

        // Add chunk delete button
        const deleteButton = document.createElement('button');
        deleteButton.className = 'delete-button';
        deleteButton.innerHTML = `<img src="${trashIconUrl}" alt="Delete" class="trash-icon">`;
        deleteButton.addEventListener('click', () => deleteChunk(chunk.id));
        chunkItem.appendChild(deleteButton);
        
        // Add click handler
        chunkItem.addEventListener('click', () => selectChunk(originalIndex, true));
        
        chunksList.appendChild(chunkItem);
    });
    
    // Show message if no chunks match search
    if (isSearchActive && chunksToDisplay.length === 0) {
        chunksList.innerHTML = '<div class="no-chunks-message">No chunks found matching your search</div>';
    }
    
    // Hide the fix invalid IDs button since all IDs are valid now
    const fixInvalidIdsContainer = document.getElementById('fix-invalid-ids');
    if (fixInvalidIdsContainer) {
        fixInvalidIdsContainer.style.display = 'none';
    }
}

// Function to select a chunk
function selectChunk(index, hasValidId = true) {
    
    // Update selected state
    selectedChunkIndex = index;
    
    // Update UI to show selected chunk
    const chunkItems = document.querySelectorAll('.chunk-item');
    chunkItems.forEach((item, i) => {
        if (i === index) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
    
    // Update chunk title - always editable
    document.getElementById('current-chunk-title').textContent = `Chunk ${index + 1}`;
    
    // Update view content
    const chunk = currentChunks[index];
    if (chunk && typeof chunk.text === 'string') {
        document.getElementById('chunk-content-view').textContent = chunk.text;
        document.getElementById('chunk-edit-textarea').value = chunk.text;
        
        // All chunks are editable now
        document.querySelector('.edit-tab').style.display = 'block';
        document.getElementById('save-changes-btn').style.display = 'inline-flex';
    } else {
        console.error("Invalid chunk data:", chunk);
        document.getElementById('chunk-content-view').textContent = "Error: Invalid chunk data";
    }
}

// Function to delete a chunk
function deleteChunk(chunkId) {
    if (!confirm("Are you sure you want to delete this chunk? \n\nThis action cannot be undone.")) {
        return;
    }

    const endpoint = `/admin/chunks/${window.chunksVars.collectionId}/${chunkId}`;
    fetch(endpoint, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) {
            console.error("Response not OK. Status:", response.status);
            throw new Error(`Failed to delete chunk: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert('Chunk deleted successfully!');
            // Reload the chunks list
            loadChunks();
        } else {
            alert('Error: ' + (data.error || 'Failed to delete chunk'));
        }
    })
    .catch(error => {
        console.error('Error deleting chunk:', error);
        loadChunks();
        alert('Error deleting chunk: ' + error.message);
    });
}

// Switch to view mode
function switchToView() {
    document.querySelector('.view-tab').classList.add('active');
    document.querySelector('.edit-tab').classList.remove('active');
    document.getElementById('chunk-content-view').style.display = 'block';
    document.getElementById('chunk-content-edit').style.display = 'none';
    document.getElementById('save-changes-btn').style.display = 'none';
}

// Switch to edit mode
function switchToEdit() {
    document.querySelector('.view-tab').classList.remove('active');
    document.querySelector('.edit-tab').classList.add('active');
    document.getElementById('chunk-content-view').style.display = 'none';
    document.getElementById('chunk-content-edit').style.display = 'block';
    document.getElementById('save-changes-btn').style.display = 'inline-flex';
}

// Save changes button
document.getElementById('save-changes-btn').addEventListener('click', function() {
    const chunk = currentChunks[selectedChunkIndex];
    const chunkId = chunk.id;
    
    if (!confirm("Are you sure you want to save these changes? \n\nThis action may result in a loss of data.")) {
        return;
    }
    
    const newText = document.getElementById('chunk-edit-textarea').value;
    const saveButton = document.getElementById('save-changes-btn');
    
    // Disable button, add disabled class, and change text
    saveButton.disabled = true;
    saveButton.classList.add('disabled');
    const originalButtonHtml = saveButton.innerHTML;
    saveButton.innerHTML = `<img src="${window.chunksVars.saveIconUrl}" alt="Save" class="save-icon"> Saving...`;
    
    // Implement the save functionality
    const endpoint = `/admin/points/${window.chunksVars.collectionId}/${chunkId}`;
    fetch(endpoint, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            text: newText
        })
    })
    .then(response => {
        if (!response.ok) {
            console.error("Response not OK. Status:", response.status);
            throw new Error(`Failed to save changes: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert('Changes saved successfully!');
            // Update the current chunk in memory
            currentChunks[selectedChunkIndex].text = newText;
            // Update the view content
            document.getElementById('chunk-content-view').textContent = newText;
            // Switch back to view mode
            switchToView();
            // Update the chunk preview in the sidebar
            const chunkItems = document.querySelectorAll('.chunk-item');
            const previewElement = chunkItems[selectedChunkIndex].querySelector('.chunk-preview');
            if (previewElement) {
                previewElement.textContent = newText.substring(0, 30) + '...';
            }
        } else {
            alert('Error: ' + (data.error || 'Failed to save changes'));
        }
    })
    .catch(error => {
        console.error('Error saving changes:', error);
        alert('Error saving changes: ' + error.message);
    })
    .finally(() => {
        // Re-enable button, remove disabled class, and restore original text
        saveButton.disabled = false;
        saveButton.classList.remove('disabled');
        saveButton.innerHTML = originalButtonHtml;
    });
});

function searchChunks(searchTerm) {
    if (!searchTerm || searchTerm.length === 0) {
        // Reset to show all chunks
        isSearchActive = false;
        filteredChunks = [];
        displayChunksList();
        return;
    }
    
    // Convert search term to lowercase for case-insensitive search
    const lowerSearchTerm = searchTerm.toLowerCase();

    // Filter chunks that contain the search term in their text
    filteredChunks = currentChunks
        .map((chunk, index) => ({ chunk, originalIndex: index }))
        .filter(chunkData => 
            chunkData.chunk.text && 
            chunkData.chunk.text.toLowerCase().includes(lowerSearchTerm)
        );
    
    isSearchActive = true;
    displayChunksList();
}
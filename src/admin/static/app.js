const uploadBox = document.getElementById('upload-box');
const fileInputArea = document.getElementById('file-input');
const files_uploaded = []; // Store uploaded files
const userName = document.getElementById('user-name');

var trashIconUrl = window.trashIconUrl || '/static/icons/trash3.svg';

// Password data storage
let passwordData = {};

// Selected collection and user
let collectionSelected = null;
let selectedUser = null;
let isAdmin = false;
let currentMode = 'scrape';
let isVectorizing = false;

// Global controller for crawl polling
let CrawlPolling = { token: 0, timeoutId: null, jobId: null, collectionId: null };

document.addEventListener('DOMContentLoaded', function() {
    // Try to load password data from session storage
    try {
        const storedPasswordData = sessionStorage.getItem('passwordData');
        if (storedPasswordData) {
            passwordData = JSON.parse(storedPasswordData);
        }
    } catch (e) {
        console.error('Error loading password data from session storage:', e);
    }

    // Load state from session storage
    let cachedState = null;
    try {
        const storedState = sessionStorage.getItem('CollectionUserState');
        if (storedState) {
            cachedState = JSON.parse(storedState);
        }
    } catch (e) {
        console.error('Error loading state from session storage:', e);
    }
    
    // Existing initialization
    clearAndDisableEverything();
    
    // Check if we're an admin user
    isAdmin = !!document.getElementById('user-select');
    
    if (isAdmin) {
        // Load users for admin, then restore state after users are loaded
        loadUsers().then(() => {
            if (cachedState && cachedState.selectedUser) {
                const userSelect = document.getElementById('user-select');
                if (userSelect) {
                    userSelect.value = cachedState.selectedUser;
                    selectedUser = cachedState.selectedUser;
                    
                    // Trigger user change which will load collections
                    handleUserChange().then(() => {
                        // After collections are loaded, restore collection selection
                        if (cachedState.selectedCollection) {
                            const collectionSelect = document.getElementById('collection-select');
                            if (collectionSelect) {
                                collectionSelect.value = cachedState.selectedCollection;
                                collectionSelected = cachedState.selectedCollection;
                                handleCollectionChange();
                            }
                        }
                    });
                }
            }
        });
    } else {
        // For institution users, load their collections then restore state
        loadCollections().then(() => {
            if (cachedState && cachedState.selectedCollection) {
                const collectionSelect = document.getElementById('collection-select');
                if (collectionSelect) {
                    collectionSelect.value = cachedState.selectedCollection;
                    collectionSelected = cachedState.selectedCollection;
                    handleCollectionChange();
                }
            }
        });
    }
    
    // Setup modal close handlers
    setupModalCloseHandlers();
    
    // Add click handler to the vectorize button
    document.getElementById('vectorize_button').addEventListener('click', vectorizeFiles);
    
    // Setup password checkbox handler for the add faculty form
    setupPasswordHandlers();
    
    // Disable the Add Collection button if we have a user select dropdown
    // (meaning we're an admin user)
    if (isAdmin) {
        const addCollectionButton = document.querySelector('.add-faculty-button');
        if (addCollectionButton) {
            addCollectionButton.disabled = true;
        }
    } else {
        // Load bot name
        loadBotName();
        loadUserName();
    }

    // --- Setup Event Listener for Deletion (Delegation) ---
    const urlInputContainer = document.getElementById('url-input-container');
    if (urlInputContainer) {
         urlInputContainer.addEventListener('click', function(event) {
            // Handle Add button click
            const addButton = event.target.closest('#add-url-button');
            if (addButton) {
                addUrl();
                return; // Stop further processing for this click
            }

            // Handle Delete button click
            const deleteButton = event.target.closest('.delete-url-button');
            if (deleteButton) {
                removeUrl(deleteButton);
                return; // Stop further processing for this click
            }
        });
    }

    // Setup copy button handler for the collection id display
    const copyButton = document.getElementById('copy-collection-id');
    if (copyButton) {
        copyButton.addEventListener('click', copyCollectionId);
    }

    // Attempt to resume any active crawl job for selected collection
    resumeActiveCrawlIfAny();

    // Setup scrape/crawl button handlers
    const scrapeButton = document.getElementById('scrape-button');
    if (scrapeButton) {
        scrapeButton.addEventListener('click', scrapeOrCrawlUrl);
    }

    const addUrlButton = document.getElementById('add-url-button');
    if (addUrlButton) {
        addUrlButton.addEventListener('click', addUrl);
    }

    const uploadBox = document.getElementById('upload-box');
    const collectionId = uploadBox.dataset.collectionId;

    // Check if we have a valid collection ID
    if (collectionId && collectionId !== "null" && collectionId !== "None" && collectionId !== "undefined") {
        collectionSelected = collectionId;
        
        // First enable the config UI
        enableBotConfig();
        enableEverything();
        // Then load collection-specific data
        // No isNameBased parameter needed here since this is for initial page load with ID from server
        loadCollectionFiles(collectionId);
        loadBotSettings(collectionId);
    } else {
        // Check if we're in admin mode
        const isAdmin = !!document.getElementById('user-select');
        
        if (isAdmin) {
            // Only disable everything for admin users
            clearAndDisableEverything();
            // Admin users select a user first, then collections are loaded
        } else {
            // For institution users with no collection ID,
            // collections are already loaded by the main DOMContentLoaded handler
            // so we just need to clear and disable everything initially
            clearAndDisableEverything(); // Initially disable
        }
    }

    // Add event listeners for password protection checkboxes
    const passwordRequiredCheckbox = document.getElementById('password-required');
    const collectionPasswordGroup = document.getElementById('collection-password-group');
    const passwordInputViewAdd = document.getElementById('password-input-view-add');
    
    if (passwordRequiredCheckbox && collectionPasswordGroup) {
        passwordRequiredCheckbox.addEventListener('change', function() {
            collectionPasswordGroup.style.display = this.checked ? 'block' : 'none';
            
            // Always show the input view in the add form
            if (passwordInputViewAdd) passwordInputViewAdd.style.display = 'block';
            
            // If unchecked, clear the password field
            if (!this.checked) {
                document.getElementById('collection-password').value = '';
            } else {
                // Focus on the password field when the checkbox is checked
                setTimeout(() => document.getElementById('collection-password').focus(), 100);
            }
        });
    }
    
    const passwordRequiredConfigCheckbox = document.getElementById('password-required-config');
    const collectionPasswordConfigGroup = document.getElementById('collection-password-config-group');
    const passwordInputViewConfig = document.getElementById('password-input-view-config');
    
    if (passwordRequiredConfigCheckbox && collectionPasswordConfigGroup) {
        passwordRequiredConfigCheckbox.addEventListener('change', function() {
            // Just show/hide the entire group
            collectionPasswordConfigGroup.style.display = this.checked ? 'block' : 'none';
            
            if (!this.checked) {
                // If unchecked, clear the password field
                document.getElementById('collection-password-config').value = '';
            } else {

                updatePasswordFieldsDisplay();
                
                // Focus on the password field
                setTimeout(() => {
                    const passwordField = document.getElementById('collection-password-config');
                    if (passwordField) {
                        passwordField.focus();
                        passwordField.placeholder = 'Enter new key';
                    }
                }, 100);
            }
        });
    }
    
    // Change password button click handlers
    const changePasswordBtnConfig = document.getElementById('change-password-btn-config');
    const changePasswordTextConfig = document.getElementById('change-password-text-config');
    if (changePasswordBtnConfig) {
        changePasswordBtnConfig.addEventListener('click', function() {
            // Show the password input view
            if (passwordSetViewConfig) passwordSetViewConfig.style.display = 'none';
            if (passwordInputViewConfig) passwordInputViewConfig.style.display = 'flex';
            
            // Focus the password field
            setTimeout(() => {
                const passwordField = document.getElementById('collection-password-config');
                if (passwordField) {
                    passwordField.focus();
                    passwordField.placeholder = 'Enter new key';
                }
            }, 100);
        });
    }

    if (changePasswordTextConfig) {
        changePasswordTextConfig.addEventListener('click', function() {
            // Show the password input view
            if (passwordSetViewConfig) passwordSetViewConfig.style.display = 'none';
            if (passwordInputViewConfig) passwordInputViewConfig.style.display = 'flex';
            
            // Focus the password field
            setTimeout(() => {
                const passwordField = document.getElementById('collection-password-config');
                if (passwordField) {
                    passwordField.focus();
                    passwordField.placeholder = 'Enter new key';
                }
            }, 100);
        });
    }
    
    // Add event listeners for show password buttons
    const showPasswordButtons = document.querySelectorAll('.show-password-btn');
    showPasswordButtons.forEach(button => {
        button.addEventListener('mousedown', function(e) {
            e.preventDefault(); // Prevent button from taking focus
            const passwordInput = this.parentElement.querySelector('input[type="password"]');
            
            // Save cursor position and current value
            const cursorPosition = passwordInput.selectionStart;
            const currentValue = passwordInput.value;
            
            // Change type to text
            passwordInput.type = 'text';
            
            // Restore cursor position after a slight delay to ensure DOM updates
            setTimeout(() => {
                // In some browsers, the value might reset when changing type, so restore it
                if (passwordInput.value !== currentValue) {
                    passwordInput.value = currentValue;
                }
                passwordInput.focus();
                passwordInput.setSelectionRange(cursorPosition, cursorPosition);
            }, 5);
            
            // Change eye icon to eye-slash icon
            const eyeIcon = this.querySelector('.eye-icon');
            if (eyeIcon) {
                eyeIcon.src = eyeIcon.src.replace('eye.svg', 'eye-slash.svg');
                eyeIcon.alt = 'Hide Password';
            }
            
            // Add event listeners to handle mouseup and mouseout
            const hidePassword = () => {
                // Save cursor position and current value again before changing back
                const cursorPos = passwordInput.selectionStart;
                const currentVal = passwordInput.value;
                
                // Change back to password type
                passwordInput.type = 'password';
                
                // Restore cursor position after a slight delay
                setTimeout(() => {
                    // In some browsers, the value might reset when changing type, so restore it
                    if (passwordInput.value !== currentVal) {
                        passwordInput.value = currentVal;
                    }
                    passwordInput.focus();
                    passwordInput.setSelectionRange(cursorPos, cursorPos);
                }, 5);
                
                // Change eye-slash icon back to eye icon
                if (eyeIcon) {
                    eyeIcon.src = eyeIcon.src.replace('eye-slash.svg', 'eye.svg');
                    eyeIcon.alt = 'Show Password';
                }
                
                document.removeEventListener('mouseup', hidePassword);
                button.removeEventListener('mouseout', hidePassword);
            };
            
            document.addEventListener('mouseup', hidePassword);
            button.addEventListener('mouseout', hidePassword);
        });
    });

    // Add cancel button event listeners
    const cancelPasswordBtnConfig = document.getElementById('cancel-password-btn-config');
    if (cancelPasswordBtnConfig) {
        cancelPasswordBtnConfig.addEventListener('click', function() {
            // Hide input view and show the "password is set" view
            if (passwordInputViewConfig) passwordInputViewConfig.style.display = 'none';
            
            // Only show the password set view if a password is already set
            const collectionId = collectionSelected || document.getElementById('upload-box').dataset.collectionId;
            
            if (passwordData[collectionId] && passwordData[collectionId].hasPassword) {
                if (passwordSetViewConfig) passwordSetViewConfig.style.display = 'flex';
                return;
            }
            
            // If no password is set, uncheck the password protection checkbox
            if (passwordRequiredConfigCheckbox) {
                passwordRequiredConfigCheckbox.checked = false;
                collectionPasswordConfigGroup.style.display = 'none';
            }
        });
    }
});

function loadUserName() {
    // Fetch user data from a dedicated endpoint
    fetch('/auth/me')
        .then(response => {
            if (!response.ok) {
                // Try to get specific error message from backend if available
                return response.json().then(err => { 
                    throw new Error(err.detail || `Failed to load username (${response.status})`); 
                }).catch(() => { 
                    // Fallback if response is not JSON or no detail provided
                    throw new Error(`Failed to load username (${response.status})`); 
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.username) {
                setUserName(data.username);
                selectedUser = data.user_id;
            } else {
                console.warn("Username not found in response from /auth/me");
                setUserName('User'); // Provide a default
            }
        })
        .catch(error => {
            console.error('Error loading user name:', error);
            setUserName('Error'); // Indicate an error occurred
        });
}

function resetUserNameContainer() {
    const userNameContainer = document.getElementById('user-name-container');
    if (userNameContainer) {
        // Clear all content from the container
        userNameContainer.innerHTML = '';
        const botNameH2 = document.getElementById('bot-name');
        if (botNameH2) {
            botNameH2.textContent = '';
        }
        const pencilIcon = document.getElementById('pencil-icon');
        if (pencilIcon) {
            pencilIcon.style.display = 'none';
        }
    }
}

function setUserName(username) {
    const userNameH2 = document.getElementById('user-name');
    const userNameContainer = document.getElementById('user-name-container');
    if (!userNameH2) return;
    userNameH2.textContent = username;
    userNameH2.title = username;
    userNameContainer.style.borderRight = '1px solid var(--border-color)';
    userNameContainer.style.paddingRight = 'var(--spacing-sm)';
}

function loadBotName() {
    const botNameH2 = document.getElementById('bot-name');
    if (!botNameH2) return;
    const pencilIcon = document.getElementById('pencil-icon');
    if (!pencilIcon) return;

    // Construct the URL with the user_id parameter if we have a selected user
    let url = '/admin/users/bot-name';
    if (selectedUser) {
        url += `?user_id=${selectedUser}`;
    }

    fetch(url)
        .then(async response => {
            if (!response.ok) {
                try {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to load bot name');
                } catch (e) {
                    throw new Error(`Failed to load bot name (${response.status})`);
                }
            }
            return response.json();
        })
        .then(data => {
            botNameH2.textContent = data.bot_name || 'No bot name set';
            pencilIcon.style.display = 'block';
        })
        .catch(error => {
            console.error('Error loading bot name:', error);
            botNameH2.textContent = 'Error loading bot name';
        });
}

// Function to load users for admin
function loadUsers() {
    // Only execute this for admin users
    const userSelect = document.getElementById('user-select');
    if (!userSelect) return Promise.resolve();

    return fetch('/admin/users')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            // Clear existing options (except the first one)
            userSelect.innerHTML = '<option value="">Select a user...</option>';
            
            // Add option for each user
            data.forEach(user => {
                const option = document.createElement('option');
                option.value = user._id;
                option.textContent = user.username;
                userSelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading users:', error);
        });
}

// Function to load collections (modified to work with user selection for admins)
function loadCollections() {
    // Check if we're in admin mode by looking for the user-select dropdown
    const isAdmin = !!document.getElementById('user-select');
    
    // For admin users, we don't load collections directly - they're loaded after user selection
    if (isAdmin) {
        return Promise.resolve();
    }
    
    // For institution users, load their collections directly into the dropdown
    return fetch('/admin/collections')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            const select = document.getElementById('collection-select');
            if (!select) {
                console.error('Collection select element not found');
                return;
            }
            
            select.innerHTML = '<option value="">Select a collection...</option>';
            
            data.forEach(collection => {
                const option = document.createElement('option');
                option.value = collection._id;
                option.textContent = collection.data_source_name;
                option.title = collection.collection_name;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Error loading collections:', error));
}

function loadCollectionFiles(collectionId) {
    if (!collectionId || collectionId === 'undefined' || collectionId === 'null') {
        console.error('Invalid collection ID provided to loadCollectionFiles');
        return;
    }
    
    // Show loading spinner
    const spinner = document.querySelector('#file-list-section .loading-spinner');
    spinner.classList.add('show');
    
    // Clear file list first
    const fileList = document.getElementById('file-list');
    fileList.innerHTML = '';
    
    // Use the ID-based endpoint - we're using MongoDB ObjectIds consistently now
    const endpoint = `/admin/points/${collectionId}`;
    
    fetch(endpoint)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to load files. Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Update file count
            const fileCount = document.getElementById('file-count');
            const count = data.length;
            fileCount.textContent = `(${count})`;
            
            // Generate file list HTML
            if (count === 0) {
                fileList.innerHTML = '<p>No files uploaded yet.</p>';
            } else {
                data.forEach(file => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    
                    // Create file name as a link to the file chunks page
                    const fileLink = document.createElement('a');
                    
                    // Special handling for URLs and regular filenames
                    let encodedFilename;
                    const isUrl = file.file_name.startsWith('http://') || file.file_name.startsWith('https://');
                    
                    if (isUrl) {
                        // For URLs, replace slashes with %2F before encoding
                        const safeFilename = file.file_name.replace(/\//g, '%2F');
                        encodedFilename = encodeURIComponent(safeFilename);
                    } else {
                        // For regular filenames, just encode normally
                        encodedFilename = encodeURIComponent(file.file_name);
                    }
                    
                    fileLink.href = `/admin/file/${collectionId}/${encodedFilename}`;
                    fileLink.textContent = file.file_name;
                    fileLink.className = 'file-link';
                    
                    // Create delete button
                    const deleteButton = document.createElement('button');
                    deleteButton.className = 'delete-button';
                    deleteButton.onclick = function(e) {
                        e.preventDefault(); // Prevent navigation if link is clicked
                        e.stopPropagation(); // Prevent event bubbling
                        deleteFile(file.file_name);
                    };
                    deleteButton.innerHTML = `<img src="${trashIconUrl}" alt="Delete" class="trash-icon">`;
                    
                    // Add elements to file item
                    fileItem.appendChild(fileLink);
                    fileItem.appendChild(deleteButton);
                    
                    fileList.appendChild(fileItem);
                });
            }
        })
        .catch(error => {
            console.error('Error loading files:', error);
            fileList.innerHTML = '<p>Error loading files. Please try again.</p>';
            // Don't show an alert here as the collection might have been deleted
        })
        .finally(() => {
            // Hide loading spinner
            spinner.classList.remove('show');
        });
}

function vectorizeFiles() {
    const collectionId = collectionSelected || uploadBox.dataset.collectionId;
    
    if (!collectionId) {
        alert('Please select a collection first');
        return;
    }
    
    if (files_uploaded.length === 0) {
        alert('No files to vectorize');
        return;
    }

    const formData = new FormData();
    
    // Add collection_id to form data
    formData.append('collection_id', collectionId);
    
    // Append each file to the form data
    files_uploaded.forEach(file => {
        formData.append('files[]', file);
    });

    // Disable file upload interactions during vectorization
    const uploadBox = document.getElementById('upload-box');
    const fileInput = document.getElementById('file-input');
    isVectorizing = true;
    uploadBox.classList.add('disabled');
    uploadBox.disabled = true;
    uploadBox.style.pointerEvents = 'none';
    if (fileInput) fileInput.disabled = true;

    // Show loading
    const vectorizeButton = document.getElementById('vectorize_button');
    vectorizeButton.innerHTML = 'Processing...';
    vectorizeButton.disabled = true;

    fetch('/admin/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert('Files vectorized successfully');
        } else {
            alert('Error vectorizing files. Please try again.');
            console.error('Error vectorizing files:', data);
        }
            
        // Clear the file preview
        const filePreview = document.getElementById('file-preview');
        filePreview.innerHTML = '';
        
        // Clear the files_uploaded array
                files_uploaded.length = 0;
        
        // Hide the vectorize button
                hideVectorizeButton();
        
        // Reload the file list
        loadCollectionFiles(collectionId);
    })
    .catch(error => {
        console.error('Error vectorizing files:', error);
        alert('Error vectorizing files. Please try again.');
        
        // Reload the file list anyways in case some files were processed
        loadCollectionFiles(collectionId);
    })
    .finally(() => {
        vectorizeButton.innerHTML = 'Vectorize';
        vectorizeButton.disabled = false;

        // Enable file upload box and enable drag and drop functionality
        uploadBox.classList.remove('disabled');
        uploadBox.disabled = false;
        uploadBox.style.pointerEvents = 'auto';
        if (fileInput) fileInput.disabled = false;
        isVectorizing = false;
    });
}

function deleteFile(filename) {
    const collectionId = collectionSelected || uploadBox.dataset.collectionId;
    
    if (!collectionId) {
        alert('Collection not selected');
        return;
    }

    if (!confirm('Are you sure you want to delete this file?')) {
        return;
    }
    
    // Special handling for URLs and regular filenames
    let encodedFilename;
    const isUrl = filename.startsWith('http://') || filename.startsWith('https://');
    
    if (isUrl) {
        // For URLs, replace slashes with %2F before encoding
        const safeFilename = filename.replace(/\//g, '%2F');
        encodedFilename = encodeURIComponent(safeFilename);
    } else {
        // For regular filenames, just encode normally
        encodedFilename = encodeURIComponent(filename);
    }
    
    const endpoint = `/admin/points/${collectionId}/${encodedFilename}`;
    
    fetch(endpoint, {
            method: 'DELETE'
        })
        .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
        alert('File deleted successfully');
        loadCollectionFiles(collectionId);
        })
        .catch(error => {
        console.error('Error deleting file:', error);
        alert('Error deleting file. Please try again.');
        });
}

// Display vectorize-button
function displayVectorizeButton() {
    document.getElementById('vectorize_button').style.display = 'block';
}

// Hide vectorize-button
function hideVectorizeButton() {
    document.getElementById('vectorize_button').style.display = 'none';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function handleFiles(event) {
    const collectionId = collectionSelected || uploadBox.dataset.collectionId;
    
    if (isVectorizing) {
        return;
    }

    if (!collectionId) {
        alert('Please select a collection first');
        return;
    }

    const files = event.dataTransfer ? event.dataTransfer.files : event.target.files;
    
    if (files.length === 0) {
            return;
        }

    const filePreview = document.getElementById('file-preview');
    
    // Process each file
    Array.from(files).forEach(file => {
        // Check file type (can be expanded to include more types)
        const acceptedTypes = ['application/pdf', 'text/plain', 'text/csv'];
        if (!acceptedTypes.includes(file.type)) {
            alert(`File type ${file.type} not supported. Please upload PDF or TXT files.`);
            return;
        }

        // Add file to the array
        files_uploaded.push(file);

        // Create preview item
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span>${file.name} (${formatFileSize(file.size)})</span>
            <button class="delete-button" onclick="removePreview(this, '${file.name}')">
                <img src="${trashIconUrl}" alt="Delete" class="trash-icon">
            </button>
        `;
        
        filePreview.appendChild(fileItem);
    });

    // Display the vectorize button if files were added
    if (files_uploaded.length > 0) {
        displayVectorizeButton();
    } else {
        hideVectorizeButton();
    }
}

function removePreview(button, fileName) {
    // Remove the file from the array
    const fileIndex = files_uploaded.findIndex(file => file.name === fileName);
    if (fileIndex > -1) {
        files_uploaded.splice(fileIndex, 1);
    }

    // Remove the file item from the DOM
    button.parentElement.remove();

    // Hide vectorize button if no files remain
    if (files_uploaded.length === 0) {
        hideVectorizeButton();
    }
}

// Close the modal
function closeModal() {
    const modal = document.getElementById('add-faculty-modal');
    const form = document.getElementById('add-faculty-form');
    modal.classList.add('hidden');
    form.reset(); // Reset form when closing
    document.body.style.overflow = 'auto'; // Restore scrolling
}

// Open the add collection modal
function openModal() {
    const modal = document.getElementById('add-faculty-modal');
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Prevent scrolling behind modal
    
    // If we're in admin mode and a user is selected, we can set a hidden user ID field
    if (selectedUser) {
        const userIdField = document.getElementById('user-id');
        if (userIdField) {
            userIdField.value = selectedUser;
        }
    }
    
    // Focus on the first input field
    setTimeout(() => {
        const firstInput = document.getElementById('bot-name');
        if (firstInput) {
            firstInput.focus();
        }
    }, 100);
}

// Open the add user modal
function openUserModal() {
    const modal = document.getElementById('add-user-modal');
    if (!modal) return; // Only proceed if the modal exists (admin only)
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Prevent scrolling behind modal
    
    // Focus on the first input field
    setTimeout(() => {
        const firstInput = document.getElementById('user-name-form-input');
        if (firstInput) {
            firstInput.focus();
        }
    }, 100);
}

function openUserPasswordModal() {
    if (isAdmin && document.getElementById('user-select').selectedIndex === 0) {
        alert('Please select a user first');
        return;
    }
    
    const modal = document.getElementById('user-password-modal');
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Prevent scrolling behind modal
}

function closeUserPasswordModal() {
    const modal = document.getElementById('user-password-modal');
    modal.classList.add('hidden');
    document.body.style.overflow = 'auto'; // Restore scrolling
}

// Handle modal close events
function submitUserPasswordForm(event) {
    event.preventDefault();
    const form = document.getElementById('user-password-form');
    const password = form.querySelector('input[name="user-password-new"]').value;
    let currentUser = selectedUser;

    if (document.getElementById('user-select') !== null) {
        currentUser = document.getElementById('user-select').value;
    }

    // Send password change request to server
    fetch(`/admin/users/${currentUser}/password`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ "password": password })
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    })
    .then(data => {
        alert('Password changed successfully');
        closeUserPasswordModal();
        form.reset();
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error changing password. Please try again.');
    });
}

// Handle modal close events
function setupModalCloseHandlers() {
    // Close faculty modal when clicking outside
    const facultyModal = document.getElementById('add-faculty-modal');
    if (facultyModal) {
        facultyModal.addEventListener('click', (e) => {
    if (e.target.id === 'add-faculty-modal') {
        closeModal();
    }
});
    }
    
    // Close user modal when clicking outside
    const userModal = document.getElementById('add-user-modal');
    if (userModal) {
        userModal.addEventListener('click', (e) => {
            if (e.target.id === 'add-user-modal') {
                closeUserModal();
            }
        });
    }
    
    // Close modals with Escape key
document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (!document.getElementById('add-faculty-modal').classList.contains('hidden')) {
        closeModal();
            }
            if (!document.getElementById('add-user-modal').classList.contains('hidden')) {
                closeUserModal();
            }
        }
    });

    // Add bot name modal handler
    const botNameModal = document.getElementById('bot-name-modal');
    if (botNameModal) {
        botNameModal.addEventListener('click', (e) => {
            if (e.target.id === 'bot-name-modal') {
                closeBotNameModal();
            }
        });
    }
}

// Setup password checkbox handlers
function setupPasswordHandlers() {
    const passwordRequired = document.getElementById('password-required');
    if (passwordRequired) {
        passwordRequired.addEventListener('change', function() {
            const passwordGroup = document.getElementById('collection-password-group');
            if (this.checked) {
                passwordGroup.style.display = 'block';
            } else {
                passwordGroup.style.display = 'none';
            }
        });
    }
    
    const passwordRequiredConfig = document.getElementById('password-required-config');
    if (passwordRequiredConfig) {
        passwordRequiredConfig.addEventListener('change', updatePasswordFieldsDisplay);
    }
}

// Add form validation functions
function validateForm(formId) {
    const form = document.getElementById(formId);
    const inputs = form.querySelectorAll('input[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        const formGroup = input.closest('.form-group');
        if (!input.value.trim()) {
            formGroup.classList.add('error');
            isValid = false;
        } else {
            formGroup.classList.remove('error');
        }
    });
    
    // Special handling for password fields when protection is enabled
    if (formId === 'add-faculty-form' || formId === 'bot-config-form') {
        const passwordRequired = document.getElementById(formId === 'add-faculty-form' ? 'password-required' : 'password-required-config');
        
        if (passwordRequired && passwordRequired.checked) {
            const passwordField = document.getElementById(formId === 'add-faculty-form' ? 'collection-password' : 'collection-password-config');
            
            if (!passwordField.value.trim()) {
                const formGroup = passwordField.closest('.form-group');
                formGroup.classList.add('error');
                isValid = false;
            }
        }
    }
    
    return isValid;
}

// Prevent default behavior for drag/drop events
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    uploadBox.addEventListener(eventName, e => e.preventDefault());
    uploadBox.addEventListener(eventName, e => e.stopPropagation());
});

// Highlight the box when a file is dragged over it
['dragenter', 'dragover'].forEach(eventName => {
    uploadBox.addEventListener(eventName, () => uploadBox.classList.add('drag-over'));
});

['dragleave', 'drop'].forEach(eventName => {
    uploadBox.addEventListener(eventName, () => uploadBox.classList.remove('drag-over'));
});

// Handle user change in admin dropdown
function handleUserChange() {
    const userSelect = document.getElementById('user-select');
    const userId = userSelect.value;
    const userName = userSelect.options[userSelect.selectedIndex].textContent || null;
    
    // Update the selected user
    selectedUser = userId;
    
    // Reset collection selection
    const collectionSelect = document.getElementById('collection-select');
    collectionSelect.innerHTML = '<option value="">Select a collection...</option>';
    collectionSelect.disabled = !userId;

    // Clear Bot Name & Pencil Icon
    const botNameH2 = document.getElementById('bot-name');
    if (botNameH2) {
        botNameH2.textContent = '';
    }
    const pencilIcon = document.getElementById('pencil-icon');
    if (pencilIcon) {
        pencilIcon.style.display = 'none';
    }
    
    // Clear and disable everything when user changes
    clearAndDisableEverything();
    
    // Don't proceed if no user is selected
    if (!userId) {
        return Promise.resolve();
    }
    
    // Fetch collections for the selected user
    const collectionsPromise = fetch(`/admin/users/${userId}/collections`)
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            // Populate collection dropdown
            data.forEach(collection => {
                const option = document.createElement('option');
                option.value = collection._id;
                option.textContent = collection.data_source_name;
                option.title = collection.collection_name;
                collectionSelect.appendChild(option);
            });
            
            // Enable the Add Collection button when a user is selected
            const addCollectionButton = document.querySelector('.add-faculty-button');
            if (addCollectionButton) {
                addCollectionButton.disabled = false;
            }
            const userConfigDropdown = document.getElementById('user-config-dropdown');
            if (userConfigDropdown) {
                userConfigDropdown.style.display = 'block';
                const dropdownButton = userConfigDropdown.querySelector('.dropdown-toggle');
                if (dropdownButton) {
                    dropdownButton.disabled = false;
                }
            }
        })
        .catch(error => {
            console.error('Error loading user collections:', error);
        });

    // Load bot name
    loadBotName();
    setUserName(userName);
    persistState();
    
    return collectionsPromise;
}

// Handle collection change in dropdown
function handleCollectionChange() {
    const collectionSelect = document.getElementById('collection-select');
    const collectionId = collectionSelect.value;
    
    // Update the selected collection
    collectionSelected = collectionId;
    
    if (collectionId) {
        
        // Enable bot configuration
        enableBotConfig();
        // Enable everything
        enableEverything();
        
        // Stop any ongoing polling from previous collection
        try { cancelPollingActiveCrawl(); } catch (e) { /* ignore */ }

        // Load collection files and settings
        loadCollectionFiles(collectionId);
        loadBotSettings(collectionId);
        persistState();

        // Reset the scrape/crawl toggle
        resetScrapeCrawlToggle();
        setupScrapeCrawlToggle();

        // Resume active crawl if any
        resumeActiveCrawlIfAny();

    } else {
        // Clear and disable everything if no collection is selected
        clearAndDisableEverything();
    }
}

// Add click handler to the vectorize button
document.getElementById('vectorize_button').addEventListener('click', vectorizeFiles);

// Add these event listeners right after the initial variable declarations at the top
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (collectionSelected && !isVectorizing) {
        uploadBox.classList.add('dragover');
    }
});

uploadBox.addEventListener('dragleave', (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadBox.classList.remove('dragover');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadBox.classList.remove('dragover');
    
    if (!collectionSelected || isVectorizing) {
        alert('Please select a collection first');
        return;
    }
    
    handleFiles(e);
});

uploadBox.addEventListener('click', () => {
    if (collectionSelected && !isVectorizing) {
        fileInputArea.click();
    } else {
        alert('Please select a collection first');
    }
});

fileInputArea.addEventListener('change', handleFiles);

function enableBotConfig() {
    const form = document.getElementById('bot-config-form');
    const inputs = form.querySelectorAll('input, textarea, button');
    inputs.forEach(input => {
        input.disabled = false;
        
        // Only set placeholders for inputs that aren't within the password view containers
        if (input.tagName.toLowerCase() !== 'button' && 
            !input.closest('#password-input-view-config')) {
            
            // Set appropriate placeholders based on input type
            if (input.tagName.toLowerCase() === 'textarea') {
                input.placeholder = 'Enter welcome message';
            } else if (input.type === 'password') {
                // Don't change placeholder for password fields - they'll be handled by loadBotSettings
            } else {
                input.placeholder = 'Enter bot name';
            }
        }
    });
    form.classList.remove('disabled');
    
    // Show and enable the dropdown for admin if a collection is selected
    const dropdown = document.getElementById('bot-config-dropdown');
    if (dropdown) {
        dropdown.style.display = 'block';
        const dropdownButton = dropdown.querySelector('.dropdown-toggle');
        if (dropdownButton) {
            dropdownButton.disabled = false;
        }
    }
}

function loadBotSettings(collectionId) {
    
    if (!collectionId || collectionId === 'undefined' || collectionId === 'null') {
        console.error('Invalid collection ID provided to loadBotSettings');
        return;
    }
    
    // Use the ID-based endpoint only - we're using MongoDB ObjectIds consistently now
    const endpoint = `/admin/collections/${collectionId}/settings`;
    
    fetch(endpoint)
        .then(response => {
            if (!response.ok) throw new Error(`Network response was not ok: ${response.status}`);
            return response.json();
        })
        .then(collection => {
            
            // Check that we received valid data
            if (!collection || typeof collection !== 'object') {
                console.error('Invalid collection data received');
                return;
            }
            
            // Populate form fields
            document.getElementById('collection-name-config').value = collection.data_source_name || '';
            document.getElementById('welcome-message-config').value = collection.welcome_message || '';
            
            // Update collection ID display
            document.getElementById('collection-id-display').textContent = collection.collection_name || collectionId;
            document.getElementById('copy-collection-id').disabled = false;
            
            // Handle password protection
            const passwordRequiredCheckbox = document.getElementById('password-required-config');
            passwordRequiredCheckbox.checked = !!collection.password_required;
            
            if (collection.password_required) {
                document.getElementById('collection-password-config').value = collection.password || '';
            }
            
            // Update password field display
            updatePasswordFieldsDisplay();
            
            // Show the delete dropdown
            const dropdown = document.getElementById('bot-config-dropdown');
            if (dropdown) {
                dropdown.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error loading collection settings:', error);
            // Don't show an alert here as the collection might have been deleted
        });
}

// Update saveBotSettings function
function saveBotSettings(event) {
    event.preventDefault();
    
    if (!validateForm('bot-config-form')) {
        return;
    }
    
    const collectionId = collectionSelected || uploadBox.dataset.collectionId;
    
    if (!collectionId) {
        alert('Please select a collection first');
        return;
    }

    // Get form data
    const collectionName = document.getElementById('collection-name-config').value;
    const welcomeMessage = document.getElementById('welcome-message-config').value;
    
    // Check if password protection is enabled
    const passwordRequired = document.getElementById('password-required-config').checked;
    
    // Prepare data
    const data = {
        data_source_name: collectionName,
        welcome_message: welcomeMessage,
        password_required: passwordRequired
    };

    // If password protection is enabled and a new password is provided
    const passwordInputView = document.getElementById('password-input-view-config');
    if (passwordRequired && passwordInputView.style.display !== 'none') {
        const password = document.getElementById('collection-password-config').value;
        if (password) {
            data.password = password;
        }
    }
    
    // Use the ID-based endpoint
    const endpoint = `/admin/collections/${collectionId}/settings`;
    
    // Submit the form
    fetch(endpoint, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        // First, check if the response is ok
        if (response.ok) {
            return response.json();
        } else {
            // For error responses, parse the JSON to get the error details
            return response.json().then(errorData => {
                throw new Error(errorData.detail || 'Failed to save bot settings');
            });
        }
    })
    .then(result => {
        if (result.success) {
            alert('Bot settings saved successfully!');
            
            // Update password data
            if (passwordRequired) {
                passwordData[collectionId] = { hasPassword: true };
            } else {
                passwordData[collectionId] = { hasPassword: false };
            }
            
            // Save password data to session storage
            try {
                sessionStorage.setItem('passwordData', JSON.stringify(passwordData));
            } catch (e) {
                console.error('Error saving password data to session storage:', e);
            }
            
            // Hide password input view and show password set view if needed
            if (passwordRequired) {
                updatePasswordFieldsDisplay();
            }
        } else {
            alert('Error: ' + (result.error || 'Failed to save bot settings'));
        }
    })
    .catch(error => {
        console.error('Error saving bot settings:', error);
        alert('Error: ' + error.message);
        loadBotSettings(collectionId);
    });
}

function editBotName() {
    const modal = document.getElementById('bot-name-modal');
    const form = document.getElementById('bot-name-form');
    const input = document.getElementById('edit-bot-name');
    
    // Pre-fill the input with current bot name
    const currentBotName = document.getElementById('bot-name').textContent;
    input.value = currentBotName === 'No bot name set' ? '' : currentBotName;
    
    // Show the modal
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Prevent scrolling
    
    // Focus on the input field
    setTimeout(() => input.focus(), 100);
}

function closeBotNameModal() {
    const modal = document.getElementById('bot-name-modal');
    const form = document.getElementById('bot-name-form');
    modal.classList.add('hidden');
    form.reset(); // Reset form when closing
    document.body.style.overflow = 'auto'; // Restore scrolling
}

function submitBotNameForm(event) {
    event.preventDefault();
    
    if (!validateForm('bot-name-form')) {
        return;
    }
    
    const newBotName = document.getElementById('edit-bot-name').value;
    const userId = selectedUser || document.getElementById('user-select')?.value;
    
    // Close the modal first for better UX
    closeBotNameModal();
    
    // Update the UI optimistically
    const botNameH2 = document.getElementById('bot-name');
    const originalBotName = botNameH2.textContent;
    botNameH2.textContent = newBotName;
    
    // Make the API call to update the bot name
    fetch(`/admin/users/bot-name`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: userId,
            bot_name: newBotName
        })
    })
    .then(async response => {
        if (!response.ok) {
            // If the response is not ok, try to get error details
            try {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to update bot name');
            } catch (e) {
                throw new Error(`Failed to update bot name (${response.status})`);
            }
        }
        return response.json();
    })
    .then(data => {
        // The optimistic update was correct
    })
    .catch(error => {
        console.error('Error updating bot name:', error);
        // Revert the optimistic update
        botNameH2.textContent = originalBotName;
        // Show error to user
        alert(`Error updating bot name: ${error.message}`);
    });
}

// Update updatePasswordFieldsDisplay to use sessionStorage passwordData
function updatePasswordFieldsDisplay() {
    const passwordRequiredConfig = document.getElementById('password-required-config');
    const passwordInputViewConfig = document.getElementById('password-input-view-config');
    const collectionPasswordConfigGroup = document.getElementById('collection-password-config-group');
    
    // Only do anything if password protection is enabled
    if (!passwordRequiredConfig || !passwordRequiredConfig.checked) {
        if (collectionPasswordConfigGroup) {
            collectionPasswordConfigGroup.style.display = 'none';
        }
        return;
    }
    
    // Show the password field container when protection is enabled
    if (collectionPasswordConfigGroup) {
        collectionPasswordConfigGroup.style.display = 'block';
        if (passwordInputViewConfig) passwordInputViewConfig.style.display = 'flex';
    }
}

function resetScrapeCrawlToggle() {
    const scrapeRadio = document.getElementById('scrape-radio');
    const crawlRadio = document.getElementById('crawl-radio');
    const addUrlButton = document.getElementById('add-url-button');
    const lastUrlInput = document.querySelector('#url-input-container .last-url-row .url-input');
    const scrapeButton = document.getElementById('scrape-button');
    const progress = document.getElementById('crawl-progress');
    const progressMessage = document.getElementById('crawl-faculty-progress-message');
    const cancelBtn = document.getElementById('cancel-crawl-btn');
    const crawlHint = document.getElementById('crawl-faculty-hint');

    // Set radios back to Scrape
    if (scrapeRadio) scrapeRadio.checked = true;
    if (crawlRadio) crawlRadio.checked = false;

    // Reset mode
    currentMode = 'scrape';

    // Reset URL inputs (clears added URLs and restores default state)
    try { resetUrlInputContainer(); } catch (e) { /* ignore */ }

    // Restore controls for scrape mode
    if (addUrlButton) {
        addUrlButton.classList.remove('hidden');
        addUrlButton.disabled = !collectionSelected;
    }
    if (lastUrlInput) {
        lastUrlInput.placeholder = 'Enter URL';
        lastUrlInput.disabled = !collectionSelected;
        lastUrlInput.value = '';
    }

    // Hide crawl UI elements
    if (progress) progress.classList.add('hidden');
    if (progressMessage) {
        progressMessage.classList.add('hidden');
        progressMessage.textContent = '';
    }
    if (cancelBtn) {
        cancelBtn.classList.add('hidden');
        cancelBtn.disabled = false;
        cancelBtn.textContent = 'Cancel';
    }
    if (crawlHint) crawlHint.classList.add('hidden');

    // Restore scrape button to default appearance and state
    if (scrapeButton) {
        scrapeButton.disabled = !collectionSelected;
        const iconElement = document.querySelector('#scrape-button .globe-icon');
        const iconSrc = iconElement ? iconElement.src : '';
        scrapeButton.innerHTML = iconSrc
            ? `<img src="${iconSrc}" alt="Globe" class="globe-icon">Scrape`
            : 'Scrape';
    }

    // Ensure the mode switch is enabled
    try { enableScrapeSwitch(); } catch (e) { /* ignore */ }
}

function setupScrapeCrawlToggle() {
    const scrapeRadio = document.getElementById('scrape-radio');
    const crawlRadio = document.getElementById('crawl-radio');
    const addUrlButton = document.getElementById('add-url-button');
    const lastUrlInput = document.querySelector('#url-input-container .last-url-row .url-input');
    const scrapeButton = document.getElementById('scrape-button');
    const progress = document.getElementById('crawl-progress');
    const progressMessage = document.getElementById('crawl-faculty-progress-message');
    const cancelBtn = document.getElementById('cancel-crawl-btn');
    const crawlHint = document.getElementById('crawl-faculty-hint');

    const setScrapeButtonLabel = (label) => {
        if (!scrapeButton) return;
        scrapeButton.textContent = label;
    };

    const applyMode = (mode) => {
        currentMode = mode;
        if (mode === 'scrape') {
            if (addUrlButton) {
                addUrlButton.classList.remove('hidden');
                addUrlButton.disabled = !collectionSelected;
            }
            if (lastUrlInput) {
                lastUrlInput.placeholder = 'Enter URL';
                lastUrlInput.disabled = !collectionSelected;
            }
            if (progress) progress.classList.add('hidden');
            if (progressMessage) {
                progressMessage.classList.add('hidden');
                progressMessage.textContent = '';
            }
            if (cancelBtn) cancelBtn.classList.add('hidden');
            if (scrapeButton) {
                scrapeButton.disabled = !collectionSelected;
                setScrapeButtonLabel('Scrape');
            }
            if (cancelBtn) cancelBtn.classList.add('hidden');
            if (crawlHint) crawlHint.classList.add('hidden');
        } else {
            if (addUrlButton) {
                addUrlButton.disabled = true;
                addUrlButton.classList.add('hidden');
            }
            const urlInputContainer = document.getElementById('url-input-container');
            if (urlInputContainer) {
                urlInputContainer.querySelectorAll('.url-input-wrapper').forEach(w => w.remove());
            }
            if (lastUrlInput) {
                lastUrlInput.value = '';
                lastUrlInput.placeholder = 'Enter base URL';
                lastUrlInput.disabled = !collectionSelected;
            }
            if (scrapeButton) {
                scrapeButton.disabled = !collectionSelected;
                setScrapeButtonLabel('Crawl');
            }
            if (crawlHint) crawlHint.classList.remove('hidden');
        }
    };

    if (scrapeRadio) scrapeRadio.addEventListener('change', () => { if (scrapeRadio.checked) applyMode('scrape'); });
    if (crawlRadio) crawlRadio.addEventListener('change', () => { if (crawlRadio.checked) applyMode('crawl'); });
    if (cancelBtn) cancelBtn.addEventListener('click', cancelActiveCrawl);

    // Initialize based on current selection
    if (crawlRadio && crawlRadio.checked) applyMode('crawl'); else applyMode('scrape');
}

function pollJobStatusToBar(jobId, collectionId) {
    const pollIntervalMs = 10_000; // 10s

    // Issue a new token for this poll session
    const myToken = ++CrawlPolling.token;
    CrawlPolling.jobId = jobId;
    CrawlPolling.collectionId = collectionId;

    const schedule = () => {
        // Schedule next tick only if token unchanged
        if (CrawlPolling.token === myToken) {
            CrawlPolling.timeoutId = setTimeout(check, pollIntervalMs);
        }
    };

    const check = () => {
        // If token changed, stop polling
        if (CrawlPolling.token !== myToken) {
            return;
        }
        fetch(`/admin/jobs/by-id/${jobId}`)
            .then(res => res.ok ? res.json() : Promise.reject(new Error('Failed to fetch job status')))
            .then(status => {
                if (!status || !status.status) return;
                const s = status.status;
                const processed = status.processed || 0;
                const total = status.total || 0;
                const message = status.message || '';

                // Update the progress bar
                const pct = total > 0 ? Math.floor((processed / total) * 100) : (s === 'succeeded' ? 100 : 0);
                const bar = document.getElementById('crawl-progress-bar');
                if (bar) {
                    bar.style.width = `${pct}%`;
                    bar.textContent = `${pct}%`;
                }

                // Update the progress message
                const progressMessage = document.getElementById('crawl-faculty-progress-message');
                if (progressMessage) {
                    if (message && message !== '') {
                        progressMessage.classList.remove('hidden');
                        progressMessage.textContent = message;
                    } else {
                        progressMessage.classList.add('hidden');
                        progressMessage.textContent = '';
                    }
                }

                if (s === 'succeeded') {
                    loadCollectionFiles(collectionId);
                    resetCrawlUI();
                    clearRememberedActiveCrawl(collectionId, jobId);
                    enableScrapeSwitch();
                } else if (s === 'failed') {
                    const err = status.error || 'The job failed.';
                    alert('Faculty scrape failed: ' + err);
                    resetCrawlUI();
                    clearRememberedActiveCrawl(collectionId, jobId);
                    enableScrapeSwitch();
                } else if (s === 'cancelling') {
                    const progressMessage = document.getElementById('crawl-faculty-progress-message');
                    progressMessage.classList.remove('hidden');
                    progressMessage.textContent = 'Cancelling...';
                    schedule();
                } else if (s === 'cancelled') {
                    loadCollectionFiles(collectionId);
                    resetCrawlUI();
                    clearRememberedActiveCrawl(collectionId, jobId);
                    enableScrapeSwitch();
                } else {
                    // queued or running – keep polling
                    schedule();
                }
            })
            .catch(() => {
                resetCrawlUI();
                enableScrapeSwitch();
                alert('Error polling job status');
            });
    };
    // First check immediately, then schedule follow-ups
    check();
}

function cancelActiveCrawl() {
    const collectionId = collectionSelected || document.getElementById('upload-box')?.dataset.collectionId;
    const remembered = getRememberedActiveCrawl(collectionId);
    if (!remembered) {
        alert('No active crawl to cancel.');
        return;
    }
    const cancelBtn = document.getElementById('cancel-crawl-btn');
    cancelBtn.disabled = true;
    cancelBtn.textContent = 'Cancelling...';
    // Show message cancelling
    const progressMessage = document.getElementById('crawl-faculty-progress-message');
    progressMessage.classList.remove('hidden');
    progressMessage.textContent = 'Cancelling...';

    fetch(`/admin/jobs/${remembered}/cancel`, { method: 'POST' })
        .then(res => {
            if (!res.ok && res.status !== 409) throw new Error('Cancel failed');
        })
        .catch(() => {})
        .finally(() => {
            // Let polling transition UI to Cancelling... and reset
        });
}

function rememberActiveCrawl(collectionId, jobId) {
    try {
        const key = 'ActiveCrawlJobs';
        const map = JSON.parse(sessionStorage.getItem(key) || '{}');
        map[collectionId] = jobId;
        sessionStorage.setItem(key, JSON.stringify(map));
    } catch(e) { /* ignore */ }
}

function getRememberedActiveCrawl(collectionId) {
    try {
        const key = 'ActiveCrawlJobs';
        const map = JSON.parse(sessionStorage.getItem(key) || '{}');
        return map[collectionId] || null;
    } catch(e) { return null; }
}

function clearRememberedActiveCrawl(collectionId, jobId) {
    try {
        const key = 'ActiveCrawlJobs';
        const map = JSON.parse(sessionStorage.getItem(key) || '{}');
        if (map[collectionId] === jobId) {
            delete map[collectionId];
            sessionStorage.setItem(key, JSON.stringify(map));
        }
    } catch(e) { /* ignore */ }
}

function resumeActiveCrawlIfAny() {
    const collectionId = collectionSelected || document.getElementById('upload-box')?.dataset.collectionId;
    if (!collectionId) return;

    // First ask backend if an active job exists
    fetch(`/admin/jobs/active?collection_id=${encodeURIComponent(collectionId)}`)
        .then(res => {
            if (!res.ok) {
                enableScrapeSwitch();
                setupScrapeCrawlToggle();
                throw new Error('Failed to query active job');
            }
            // Clear any stale remembered id
            const remembered = getRememberedActiveCrawl(collectionId);
            if (remembered) clearRememberedActiveCrawl(collectionId, remembered);
            return res.json();
        })
        .then(active => {
            if (active && active.id) {
                // Switch to crawl mode and adjust UI
                const crawlRadio = document.getElementById('crawl-radio');
                const scrapeRadio = document.getElementById('scrape-radio');
                if (crawlRadio) crawlRadio.checked = true;
                if (scrapeRadio) scrapeRadio.checked = false;
                setupScrapeCrawlToggle();
                disableScrapeSwitch();
                startCrawlChangeUI();
                rememberActiveCrawl(collectionId, active.id);
                pollJobStatusToBar(active.id, collectionId);
            } else {
                // No active job on backend; clear any stale remembered id
                const remembered = getRememberedActiveCrawl(collectionId);
                if (remembered) clearRememberedActiveCrawl(collectionId, remembered);
                enableScrapeSwitch();
                setupScrapeCrawlToggle();
            }
        })
        .catch(() => { /* ignore */ });
}
// Close dropdown when clicking outside
document.addEventListener('click', (event) => {
    if (!event.target.matches('.dropdown-toggle') && !event.target.matches('.dots-icon')) {
        const dropdowns = document.getElementsByClassName('dropdown-content');
        Array.from(dropdowns).forEach(dropdown => {
            if (dropdown.classList.contains('show')) {
                dropdown.classList.remove('show');
            }
        });
    }
});

// Helper function to clear and disable everything
function clearAndDisableEverything() {
    // Disable upload section card
    const uploadSection = document.getElementById('upload-section');
    uploadSection.classList.add('disabled');
    
    // Disable upload box
    const uploadBox = document.getElementById('upload-box');
    uploadBox.classList.add('disabled');
    
    // Clear and hide file preview and vectorize button
    const filePreview = document.getElementById('file-preview');
    filePreview.innerHTML = '';
    const vectorizeButton = document.getElementById('vectorize_button');
    vectorizeButton.style.display = 'none';

    // Disable bot configuration card and form
    const botConfigSection = document.getElementById('bot-config-section');
    botConfigSection.classList.add('disabled');
    
    const botConfigForm = document.getElementById('bot-config-form');
    botConfigForm.classList.add('disabled');
    document.getElementById('collection-name-config').disabled = true;
    document.getElementById('welcome-message-config').disabled = true;
    document.getElementById('password-required-config').disabled = true;
    document.getElementById('save-bot-settings').disabled = true;
    
    // Clear and disable collection ID display
    document.getElementById('collection-id-display').textContent = 'Please select a data source first';
    document.getElementById('copy-collection-id').disabled = true;

    // Disable URL scraper card and inputs
    const urlScrapeSection = document.getElementById('url-scrape-section');
    urlScrapeSection.classList.add('disabled');
    

    const urlInputs = document.querySelectorAll('.url-input');
    urlInputs.forEach(input => {
        input.classList.add('disabled');
        input.disabled = true;
    });
    const scrapeButton = document.getElementById('scrape-button');
    const cancelCrawlButton = document.getElementById('cancel-crawl-btn');
    const addUrlButton = document.getElementById('add-url-button');
    scrapeButton.disabled = true;
    addUrlButton.disabled = true;
    cancelCrawlButton.classList.add('hidden');

    // Hide bot config dropdown if it exists
    const botConfigDropdown = document.getElementById('bot-config-dropdown');
    if (botConfigDropdown) {
        botConfigDropdown.style.display = 'none';
    }

    // Clear file list
    const fileList = document.getElementById('file-list');
    fileList.innerHTML = '';
    document.getElementById('file-count').textContent = '';

    // Disable file chunks section card
    const fileChunksSection = document.getElementById('file-list-section');
    fileChunksSection.classList.add('disabled');

    // Disable scrape section dropdown
    const scrapeSectionDropdown = document.getElementById('scrape-section-dropdown');
    if (scrapeSectionDropdown) {
        scrapeSectionDropdown.style.display = 'none';
    }

    // Disable crawl faculty section
    const crawlFacultySection = document.getElementById('crawl-faculty-section');
    if (crawlFacultySection) {
        crawlFacultySection.classList.add('disabled');
    }
}

// Helper function to enable everything
function enableEverything() {
    // Enable upload section card
    const uploadSection = document.getElementById('upload-section');
    uploadSection.classList.remove('disabled');
    
    // Enable upload box
    const uploadBox = document.getElementById('upload-box');
    uploadBox.classList.remove('disabled');
    uploadBox.style.pointerEvents = 'auto';
    uploadBox.style.opacity = '1';

    // Enable bot configuration card and form
    const botConfigSection = document.getElementById('bot-config-section');
    botConfigSection.classList.remove('disabled');
    
    const botConfigForm = document.getElementById('bot-config-form');
    botConfigForm.classList.remove('disabled');
    document.getElementById('collection-name-config').disabled = false;
    document.getElementById('welcome-message-config').disabled = false;
    document.getElementById('password-required-config').disabled = false;
    document.getElementById('save-bot-settings').disabled = false;

    // Enable URL scraper card and inputs
    const urlInputs = document.querySelectorAll('.url-input');
    urlInputs.forEach(input => {
        input.classList.remove('disabled');
        input.disabled = false;
    });
    const urlScrapeSection = document.getElementById('url-scrape-section');
    urlScrapeSection.classList.remove('disabled');
    
    const scrapeButton = document.getElementById('scrape-button');
    const addUrlButton = document.getElementById('add-url-button');
    scrapeButton.disabled = false;
    addUrlButton.disabled = false;

    // Enable file chunks section card
    const fileChunksSection = document.getElementById('file-list-section');
    fileChunksSection.classList.remove('disabled');

    // Show bot config dropdown if it exists
    const botConfigDropdown = document.getElementById('bot-config-dropdown');
    if (botConfigDropdown) {
        botConfigDropdown.style.display = 'block';
    }
}

function disableScrapeSwitch() {
    const scrapeRadio = document.getElementById('scrape-radio');
    if (scrapeRadio) scrapeRadio.disabled = true;
    const crawlRadio = document.getElementById('crawl-radio');
    if (crawlRadio) crawlRadio.disabled = true;
}

function enableScrapeSwitch() {
    const scrapeRadio = document.getElementById('scrape-radio');
    if (scrapeRadio) scrapeRadio.disabled = false;
    const crawlRadio = document.getElementById('crawl-radio');
    if (crawlRadio) crawlRadio.disabled = false;
}

function cancelPollingActiveCrawl() {
    // Invalidate any ongoing poll loop and clear scheduled timeout
    CrawlPolling.token++;
    if (CrawlPolling.timeoutId) {
        clearTimeout(CrawlPolling.timeoutId);
        CrawlPolling.timeoutId = null;
    }
    CrawlPolling.jobId = null;
    CrawlPolling.collectionId = null;
}

function startCrawlChangeUI() {
    // Show UI and poll
    const progress = document.getElementById('crawl-progress');
    const bar = document.getElementById('crawl-progress-bar');
    progress.classList.remove('hidden');
    bar.style.width = '0%';
    bar.textContent = '0%';

    // Hide start, show running badge
    const startBtn = document.getElementById('scrape-button');
    startBtn.disabled = true;
    startBtn.textContent = 'Running...';

    // Disable the url input
    const urlInput = document.getElementById('url-input-last');
    urlInput.disabled = true;

    // Show the cancel button
    const cancelBtn = document.getElementById('cancel-crawl-btn');
    cancelBtn.classList.remove('hidden');
    cancelBtn.textContent = 'Cancel';

    // Show the progress message
    const progressMessage = document.getElementById('crawl-faculty-progress-message');
    progressMessage.classList.remove('hidden');
    progressMessage.textContent = "Crawling...";
}

function resetCrawlUI() {
    // Enable the url input
    const urlInput = document.getElementById('url-input-last');
    urlInput.disabled = false;

    const progressMessage = document.getElementById('crawl-faculty-progress-message');
    progressMessage.classList.add('hidden');
    progressMessage.textContent = '';

    const progress = document.getElementById('crawl-progress');
    progress.classList.add('hidden');

    const bar = document.getElementById('crawl-progress-bar');
    bar.style.width = '0%';
    bar.textContent = '0%';

    const startBtn = document.getElementById('scrape-button');
    startBtn.disabled = false;
    startBtn.textContent = 'Crawl';

    const cancelBtn = document.getElementById('cancel-crawl-btn');
    cancelBtn.classList.add('hidden');
    cancelBtn.disabled = false;
}

function addUrl() {
    const urlInputContainer = document.getElementById('url-input-container');
    const lastUrlRow = urlInputContainer?.querySelector('.last-url-row');
    const currentInput = lastUrlRow?.querySelector('.url-input');

    // Ensure necessary elements exist
    if (!urlInputContainer || !lastUrlRow || !currentInput) {
        console.error("Add URL: Could not find necessary container elements.");
        return;
    }

    // Ensure trash icon path is available
    if (!trashIconUrl) {
         console.error("Trash icon source path is missing!");
         alert("Error: Cannot add URL field, icon path missing.");
         return;
    }

    const urlValue = currentInput.value.trim();

    // Basic validation
    if (urlValue === "") {
        currentInput.focus();
        return;
    }

    // Validate URL format
    try {
        new URL(urlValue);
    } catch(e) {
        alert(`Invalid URL format: ${urlValue}`);
        currentInput.focus();
        return;
    }

    // --- Create the Elements ---

    // 1. Create the wrapper div
    const wrapperDiv = document.createElement('div');
    wrapperDiv.classList.add('url-input-wrapper');

    // 2. Create the read-only input field
    const newUrlDisplayInput = document.createElement('input');
    newUrlDisplayInput.setAttribute('type', 'text');
    newUrlDisplayInput.setAttribute('value', urlValue);
    newUrlDisplayInput.setAttribute('readonly', true); // Make read-only
    newUrlDisplayInput.classList.add('url-input', 'added-url');
    // Optional: Add name for form submission if needed
    // newUrlDisplayInput.setAttribute('name', 'scraped_urls[]');

    // 3. Create the delete button
    const deleteButton = document.createElement('button');
    deleteButton.setAttribute('type', 'button'); // Good practice for buttons not submitting forms
    deleteButton.classList.add('delete-url-button');
    deleteButton.setAttribute('aria-label', 'Delete URL'); // For accessibility

    // 4. Create the trash icon image
    const trashImage = document.createElement('img');
    trashImage.setAttribute('src', trashIconUrl); // Use the stored path
    trashImage.setAttribute('alt', 'Delete');
    trashImage.classList.add('trash-icon');

    // --- Assemble and Insert ---

    // 5. Append icon to button, then input and button to wrapper
    deleteButton.appendChild(trashImage);
    wrapperDiv.appendChild(newUrlDisplayInput);
    wrapperDiv.appendChild(deleteButton);

    // 6. Insert the new wrapper *before* the last row element
    urlInputContainer.insertBefore(wrapperDiv, lastUrlRow);

    // --- Cleanup ---

    // 7. Clear the input field in the last row
    currentInput.value = '';

    // 8. Set focus back to the input field for the next entry
    currentInput.focus();

}

// --- Function to Remove URL ---
// This function is called by the event listener when a delete button is clicked
function removeUrl(deleteButton) {
    // Find the closest parent wrapper div
    const wrapperToRemove = deleteButton.closest('.url-input-wrapper');
    if (wrapperToRemove) {
        const removedUrl = wrapperToRemove.querySelector('.url-input')?.value || 'unknown';
        wrapperToRemove.remove(); // Remove the entire wrapper from the DOM
    } else {
        console.error("Could not find the URL wrapper to remove.");
    }
}


function resetUrlInputContainer() {
    const urlInputContainer = document.getElementById('url-input-container');
    const lastUrlRow = urlInputContainer.querySelector('.last-url-row');
    const lastUrlInput = lastUrlRow?.querySelector('.url-input'); // Use optional chaining

    if (!urlInputContainer || !lastUrlRow || !lastUrlInput) {
        console.error("Could not find necessary elements to reset URL input.");
        return;
    }

    // 1. Remove all the previously added URL inputs
    const urlInputWrapper = urlInputContainer.querySelectorAll('.url-input-wrapper');
    urlInputWrapper.forEach(wrapper => wrapper.remove());

    // 2. Clear the value of the input field in the last row
    lastUrlInput.value = '';

    // 3. Ensure the last input and button are enabled/disabled correctly
    const addUrlButton = lastUrlRow.querySelector('#add-url-button');
    const isCollectionSelected = !!document.getElementById('collection-select')?.value; // Example check
    lastUrlInput.disabled = !isCollectionSelected;
    addUrlButton.disabled = !isCollectionSelected;

}


function scrapeOrCrawlUrl() {
    const urlInputContainer = document.getElementById('url-input-container');
    const urlInputs = document.querySelectorAll('#url-input-container .url-input.added-url');
    const lastInput = document.querySelector('#url-input-container .last-url-row .url-input');
    const scrapeButton = document.getElementById('scrape-button');
    const addUrlButton = document.getElementById('add-url-button');
    const progress = document.getElementById('crawl-progress');
    const progressMessage = document.getElementById('crawl-faculty-progress-message');
    const cancelBtn = document.getElementById('cancel-crawl-btn');

    if (currentMode === 'crawl') {
        const baseUrl = (lastInput?.value || '').trim();
        if (!baseUrl) {
            alert('Please enter a base URL to crawl.');
            lastInput?.focus();
            return;
        }
        try { new URL(baseUrl); } catch { alert(`Invalid URL format: ${baseUrl}`); lastInput?.focus(); return; }

        // Disable the scrape switch
        disableScrapeSwitch();

        // Change UI to crawl with function
        startCrawlChangeUI();

        const collectionId = collectionSelected || document.getElementById('upload-box')?.dataset.collectionId;
        if (!collectionId) { alert('Please select a collection first'); return; }

        if (scrapeButton) { scrapeButton.disabled = true; scrapeButton.textContent = 'Crawling...'; }
        if (addUrlButton) { addUrlButton.disabled = true; addUrlButton.classList.add('hidden'); }
        if (lastInput) lastInput.disabled = true;
        if (progress) progress.classList.remove('hidden');
        if (progressMessage) { progressMessage.classList.remove('hidden'); progressMessage.textContent = 'Started.'; }
        if (cancelBtn) cancelBtn.classList.remove('hidden');

        fetch('/admin/crawl-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: baseUrl, collection_id: collectionId })
        })
        .then(res => res.ok ? res.json() : Promise.reject(new Error('Failed to start crawl job')))
        .then(data => {
            if (data.success && data.job_id) {
                rememberActiveCrawl(collectionId, data.job_id);
                pollJobStatusToBar(data.job_id, collectionId);
            } else {
                if (progress) progress.classList.add('hidden');
                if (progressMessage) { progressMessage.classList.add('hidden'); progressMessage.textContent = ''; }
                if (cancelBtn) cancelBtn.classList.add('hidden');
                alert(data.message || 'Failed to start crawl');
            }
        })
        .catch(err => {
            if (progress) progress.classList.add('hidden');
            if (progressMessage) { progressMessage.classList.add('hidden'); progressMessage.textContent = ''; }
            if (cancelBtn) cancelBtn.classList.add('hidden');
            console.error(err);
            alert('Error starting crawl');
        });
        return;
    } else {
        // Disable the crawl switch
        disableScrapeSwitch();

        const allInputs = [...urlInputs]; // Convert NodeList to Array
        if (lastInput) {
            allInputs.push(lastInput); // Add the last input field to the list to check
        }

        const urlsToScrape = [];

        allInputs.forEach(input => {
            const trimmedValue = input.value.trim();

            // Skip empty strings
            if (trimmedValue === "") {
                return; // Skips this iteration of the forEach loop
            }

            try {
                // Validate the URL format. This is the standard JS way.
                // It will throw a TypeError if the format is invalid.
                new URL(trimmedValue);

                // If new URL() didn't throw an error, the format is valid.
                // Add it to the list.
                urlsToScrape.push(trimmedValue);

            } catch (e) {
                // If new URL() threw an error, the format is invalid.
                console.warn(`Skipping invalid URL format: ${trimmedValue}`);
            }
        });

        // Now proceed with the urlsToScrape array...
        if (urlsToScrape.length === 0) {
            alert("Please enter at least one valid URL to scrape.");
            return;
        }

        // Store the original icon source before changing the button
        const iconElement = document.querySelector('#scrape-button .globe-icon');
        const iconSrc = iconElement ? iconElement.src : '';

        // Reset the URL input container
        resetUrlInputContainer();

        // Disable buttons during scrape
        scrapeButton.disabled = true;
        addUrlButton.disabled = true;
        scrapeButton.textContent = 'Scraping...';

        // Get collection ID
        const collectionId = collectionSelected || document.getElementById('upload-box').dataset.collectionId;
        
        if (!collectionId) {
            alert('Please select a collection first');
            return;
        }

        // Send the request
        fetch('/admin/scrape-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ urls: urlsToScrape, collection_id: collectionId })
        })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.error) {
                // Error from server
                alert('Error: ' + data.error);
            }
            else if (data.success == false) {
                // Failed to scrape URLs
                if (data.message && data.message.length > 0) {
                    alert(data.message);
                }
                else {
                    alert('Failed to scrape URLs.\nPlease try again.');
                }

                loadCollectionFiles(collectionId);
            }
            else {
                // Full success
                alert('URL scraped and vectorized successfully!');
                loadCollectionFiles(collectionId);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            enableScrapeSwitch();
            alert('Error: ' + (error.message || 'Failed to scrape URL'));
        })
        .finally(() => {
            // Re-enable button and restore text with icon
            scrapeButton.disabled = false;
            addUrlButton.disabled = false;
            scrapeButton.innerHTML = iconSrc ? 
                `<img src="${iconSrc}" alt="Globe" class="globe-icon">Scrape` : 
                `Scrape`;

            enableScrapeSwitch();
        });
    }
}

function closeUserModal() {
    const modal = document.getElementById('add-user-modal');
    const form = document.getElementById('add-user-form');
    modal.classList.add('hidden');
    form.reset(); // Reset form when closing
    document.body.style.overflow = 'auto'; // Restore scrolling
}

// Function to toggle dropdown menu visibility
function toggleDropdownHere(event) {
    event.stopPropagation(); // Prevent the click from propagating
    const dropdown = event.currentTarget.nextElementSibling;
    dropdown.classList.toggle('show');
}

// Function to confirm and delete a collection
function confirmDeleteCollection() {
    const collectionId = collectionSelected;
    
    if (!collectionId) {
        alert('No collection selected');
        return;
    }
    
    // Ask for confirmation
    if (!confirm('Are you sure you want to delete this data source? This will permanently delete all files and settings. This action cannot be undone.')) {
        return;
    }
    
    // Show loading state
    const dropdown = document.querySelector('.dropdown-content');
    if (dropdown) dropdown.classList.remove('show');
    
    // Send delete request to server
    fetch(`/admin/collections/${collectionId}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert('Data source deleted successfully');
            
            // Reset UI state
            collectionSelected = null;
            
            // Reset collection selection dropdown if it exists
            const collectionSelect = document.getElementById('collection-select');
            if (collectionSelect) {
                // Remove the deleted collection from the dropdown
                const options = collectionSelect.querySelectorAll('option');
                options.forEach(option => {
                    if (option.value === collectionId) {
                        option.remove();
                    }
                });
                
                // Select the first option
                collectionSelect.selectedIndex = 0;
            }
            
            // Clear and disable everything
            clearAndDisableEverything();
            
            // Update persisted state
            persistState();
        } else {
            alert('Error: ' + (data.error || 'Unknown error occurred'));
        }
    })
    .catch(error => {
        console.error('Error deleting collection:', error);
        alert('Error deleting collection. Please try again.');
    });
}

// Function to confirm and delete a user
function confirmDeleteUser() {
    if (isAdmin && document.getElementById('user-select').selectedIndex === 0) {
        alert('Please select a user first');
        return;
    }

    let userId;
    if (isAdmin) {
        const userSelect = document.getElementById('user-select');
        userId = userSelect.value;
    }
    else {
        userId = selectedUser;
    }
    

    if (!userId) {
        alert('No user selected.');
        return;
    }
    
    // Ask for confirmation
    if (!confirm('Are you sure you want to delete the user? This will permanently delete all associated collections and settings. This action cannot be undone.')) {
        return;
    }
    
    // Show loading state
    const dropdown = document.querySelector('.dropdown-content');
    if (dropdown) dropdown.classList.remove('show');
    
    // Send delete request to server
    fetch(`/admin/users/${userId}`, {
        method: 'DELETE'
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    })
    .then(data => {
        if (data.success) {
            alert('User deleted successfully');

            if (!isAdmin) {
                logout();
                
                // Logout the user
                fetch('/auth/logout', {
                    method: 'POST'
                })
                .then(() => {
                    window.location.href = '/auth/login';
                });
            }
            
            // Reset UI state
            selectedUser = null;
            resetUserNameContainer();
            
            // Reset user selection dropdown if it exists
            const userSelect = document.getElementById('user-select');
            if (userSelect) {
                // Remove the deleted user from the dropdown
                const options = userSelect.querySelectorAll('option');
                options.forEach(option => {
                    if (option.value === userId) {
                        option.remove();
                    }
                });
                
                // Select the first option
                userSelect.selectedIndex = 0;
            }

            // Reset the collection selection dropdown
            const collectionSelect = document.getElementById('collection-select');
            if (collectionSelect) {
                collectionSelect.selectedIndex = 0;
            }
            
            // Clear and disable everything
            clearAndDisableEverything();
            
            // Update persisted state
            persistState();
        } else {
            alert('Error: ' + (data.error || 'Unknown error occurred'));
        }
    })
    .catch(error => {
        console.error('Error deleting collection:', error);
        alert('Error deleting collection. Please try again.');
    });
}

// Function to submit the Add Collection form
function submitFacultyForm(event) {
    event.preventDefault();
    
    if (!validateForm('add-faculty-form')) {
        return;
    }
    
    // Get form data
    const collectionName = document.getElementById('collection-name').value;
    const welcomeMessage = document.getElementById('welcome-message').value;
    const passwordRequired = document.getElementById('password-required').checked;
    
    // Create FormData object instead of JSON
    const formData = new FormData();
    formData.append('data_source_name', collectionName);
    formData.append('welcome_message', welcomeMessage);
    
    // Handle checkbox - backend expects "on" or nothing
    if (passwordRequired) {
        formData.append('password_required', 'on');
        
        // Add password if required - use collection_password as the field name
        const password = document.getElementById('collection-password').value;
        if (password) {
            formData.append('collection_password', password);
        }
    }
    
    // If we're in admin mode and a user is selected, we need to specify the owner
    if (selectedUser) {
        formData.append('owner_id', selectedUser);
    }
    
    // Submit the form
    fetch('/admin/collections', {
        method: 'POST',
        // Remove the Content-Type header to let the browser set it with the boundary
        body: formData
    })
    .then(response => {
        // First, check if the response is ok
        if (response.ok) {
            return response.json();
        } else {
            // For error responses, parse the JSON to get the error details
            return response.json().then(errorData => {
                throw new Error(errorData.detail || 'Failed to add collection');
            });
        }
    })
    .then(result => {
        if (result.success) {
            alert('Collection added successfully!');
            closeModal();
            
            // Reload collections and auto-select the newly created one
            const newCollectionId = result.id;
            const reload = isAdmin ? handleUserChange() : loadCollections();
            Promise.resolve(reload)
                .then(() => {
                    const collectionSelect = document.getElementById('collection-select');
                    if (!collectionSelect) return;
                    // Set the dropdown to the new collection id
                    collectionSelect.value = newCollectionId;
                    // Update state and trigger downstream loading/UI
                    collectionSelected = newCollectionId;
                    handleCollectionChange();
                })
                .catch(() => {
                    // As a fallback, just reload files/settings if we have the id
                    if (newCollectionId) {
                        collectionSelected = newCollectionId;
                        handleCollectionChange();
                    }
                });
        } else {
            alert('Error: ' + (result.error || 'Failed to add collection'));
        }
    })
    .catch(error => {
        console.error('Error adding collection:', error);
        alert('Error: ' + error.message);
    });
}

// Function to submit the Add User form
function submitUserForm(event) {
    event.preventDefault();
    
    if (!validateForm('add-user-form')) {
        return;
    }
    
    // Get form data
    const username = document.getElementById('user-name-form-input').value;
    const password = document.getElementById('user-password').value;
    const botName = document.getElementById('bot-name-user').value;

    // Create FormData object instead of JSON
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('bot_name', botName);

    // Submit the form
    fetch('/admin/users', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        // First, check if the response is ok
        if (response.ok) {
            return response.json();
        } else {
            // For error responses, parse the JSON to get the error details
            return response.json().then(errorData => {
                throw new Error(errorData.detail || 'Failed to add user');
            });
        }
    })
    .then(result => {
        if (result.success) {
            alert('User added successfully!');
            closeUserModal();
            
            // Reload the users
            const newUserId = result.id;
            Promise.resolve(loadUsers())
                .then(() => {
                    const userSelect = document.getElementById('user-select');
                    if (!userSelect) return;
                    userSelect.value = newUserId;
                    selectedUser = newUserId;
                    handleUserChange();
                })
                .catch(() => {
                    // Fallback: set state and trigger if possible
                    const userSelect = document.getElementById('user-select');
                    if (userSelect) {
                        userSelect.value = newUserId;
                        selectedUser = newUserId;
                        handleUserChange();
                    }
                });
        } else {
            alert('Error: ' + (result.error || 'Failed to add user'));
        }
    })
    .catch(error => {
        console.error('Error adding user:', error);
        alert('Error: ' + error.message);
    });
}


function persistState() {
    if (isAdmin) {
        const state = {
            selectedUser: selectedUser,
            selectedCollection: collectionSelected
        };
        sessionStorage.setItem('CollectionUserState', JSON.stringify(state));
    }
    else {
        const state = {
            selectedUser: null,
            selectedCollection: collectionSelected
        };
        sessionStorage.setItem('CollectionUserState', JSON.stringify(state));
    }
}

function logout() {
    // Clear the cached state
    clearCachedState();
}

// Function to copy collection ID to clipboard
function copyCollectionId() {
    const collectionIdElement = document.getElementById('collection-id-display');
    const collectionId = collectionIdElement.textContent;
    
    // Check if we have a valid collection ID (not the placeholder text)
    if (!collectionId || collectionId === 'Please select a data source first') {
        alert('No collection ID to copy');
        return;
    }
    
    // Use the modern clipboard API if available
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(collectionId).then(() => {
            alert('Collection ID copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy: ', err);
            alert('Failed to copy collection ID');
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = collectionId;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            alert('Collection ID copied to clipboard!');
        } catch (err) {
            console.error('Failed to copy: ', err);
            alert('Failed to copy collection ID');
        }
        document.body.removeChild(textArea);
    }
}

function clearCachedState() {
    sessionStorage.removeItem('CollectionUserState');
}
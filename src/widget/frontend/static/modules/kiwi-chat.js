/**
 * Kiwi Chat Module
 * Handles chat functionality, message sending and receiving
 */

/**
 * Deletes chat messages from the frontend
 */
function deleteChatFrontend() {
    const listItemsToRemove = getContext().querySelectorAll("li.chat");

    if (listItemsToRemove.length > 0) {
        for (let i = 1; i < listItemsToRemove.length; i++) {
            listItemsToRemove[i].remove();
        }
    }
}

/**
 * Deletes the chat history in backend and frontend
 * @param {string} thread_id - The thread ID to delete
 */
async function deleteChat(thread_id) {
    deleteChatFrontend();

    if (thread_id) {
        try {
            const response = await fetch(`${domain}/delete_chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ thread_id: thread_id })
            });
            
            const data = await response.json();
            
            if (data.success) {
                deleteThreadID();
                dropdownMenu.classList.toggle("hidden");
            } else {
                console.error("Fehler beim Löschen des Chats:", data.error);
            }
        } catch (error) {
            console.error("Fehler beim Löschen des Chats:", error);
        }
    }
}

/**
 * Builds chat from chat history
 * @param {string} thread_id - The thread ID to build chat from
 */
async function buildChat(thread_id) {
    try {
        const response = await fetch(`${domain}/get_chat_history?thread_id=${thread_id}`);
        const data = await response.json();
        const messages = data.messages;

        // Display the chat history in the frontend
        for (let i = 0; i < messages.length; i++) {
            if (i % 2 === 0) {
                sendInputMessage(messages[i]);
            } else {
                sendOutputMessage(messages[i]);
            }
        }
    } catch (error) {
        console.error("Fehler beim Laden des Chatverlaufs:", error);
    }
}

/**
 * Shows loading animation while waiting for response
 */
function showLoadingAnimation() {
    let newOutputMessage = document.createElement("li");
    newOutputMessage.classList.add("chat", "outgoing");
    newOutputMessage.id = "loading-message";

    const icon = document.createElement("span");
    icon.classList.add("material-symbols-outlined");
    icon.textContent = "smart_toy";

    let image = document.createElement("div");
    image.innerHTML = "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 200 200\"><circle fill=\"#C72426\" stroke=\"#C72426\" stroke-width=\"15\" r=\"15\" cx=\"40\" cy=\"65\"><animate attributeName=\"cy\" calcMode=\"spline\" dur=\"2\" values=\"65;135;65;\" keySplines=\".5 0 .5 1;.5 0 .5 1\" repeatCount=\"indefinite\" begin=\"-.4\"></animate></circle><circle fill=\"#C72426\" stroke=\"#C72426\" stroke-width=\"15\" r=\"15\" cx=\"100\" cy=\"65\"><animate attributeName=\"cy\" calcMode=\"spline\" dur=\"2\" values=\"65;135;65;\" keySplines=\".5 0 .5 1;.5 0 .5 1\" repeatCount=\"indefinite\" begin=\"-.2\"></animate></circle><circle fill=\"#C72426\" stroke=\"#C72426\" stroke-width=\"15\" r=\"15\" cx=\"160\" cy=\"65\"><animate attributeName=\"cy\" calcMode=\"spline\" dur=\"2\" values=\"65;135;65;\" keySplines=\".5 0 .5 1;.5 0 .5 1\" repeatCount=\"indefinite\" begin=\"0\"></animate></circle></svg>";

    newOutputMessage.appendChild(icon);
    newOutputMessage.appendChild(image);

    chatbox.appendChild(newOutputMessage);
    chatbox.scrollTop = chatbox.scrollHeight;
}

/**
 * Hides loading animation
 */
function hideLoadingAnimation() {
    const loadingMessage = getContext().getElementById("loading-message");
    if (loadingMessage) {
        loadingMessage.remove();
    }
}

/**
 * Handles sending message to server and getting response
 * @param {string} message - User message to send
 * @param {File} file - Optional file to send
 */
async function handleSendMessage(message, file) {
    if (message !== "") {
        sendInputMessage();
        showLoadingAnimation();
        const base64Data = await getBase64(file);
        await sendDataToServer(message, base64Data);
        hideLoadingAnimation();
        chatbox.scrollTop = chatbox.scrollHeight;
    }
}

/**
 * Convert file to base64
 * @param {File} file - File to convert
 * @returns {Promise<string>} Base64 representation of file
 */
async function getBase64(file) {
    if (file) {
        const reader = new FileReader();

        return new Promise((resolve, reject) => {
            reader.onload = () => {
                resolve(reader.result);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    } else {
        return "";
    }
}

/**
 * Searches the web using DuckDuckGo
 * @param {string} query - Search query
 */
async function searchDuckDuckGo(query) {
    const url = `https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_redirect=1&no_html=1&kl=de-de`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        let outputMessage = "";

        if (data.Answer) {
            outputMessage = data.Answer;
        } else if (data.AbstractText) {
            outputMessage = data.AbstractText;
        } else if (data.RelatedTopics.length > 0) {
            outputMessage = data.RelatedTopics[0].Text;
        } else if(data.AbstractURL){
            outputMessage = data.AbstractURL;
        }
        else{
            outputMessage = "Die Websuche lieferte keine Treffer.";
        }

        sendOutputMessage(outputMessage);
        chatbox.scrollTop = chatbox.scrollHeight;
    } catch (error) {
        console.error("Fehler:", error);
        sendOutputMessage('Sorry, something went wrong.');
    }
}

/**
 * Sends data to server for processing
 * @param {string} userInput - User input message
 * @param {string} base64Data - Base64 encoded file data
 */
async function sendDataToServer(userInput, base64Data) {
    if(websearchButton.style.color === 'blue') {
        await searchDuckDuckGo(userInput);
    } else {
        try {
            let thread_id = getThreadID();

            if (!thread_id) {
                thread_id = generateThreadId();
                setThreadID(thread_id);
            }

            const response = await fetch(`${domain}/generate_answer`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: userInput,
                    data: base64Data,
                    collection: collection,
                    thread_id: thread_id
                }),
            });

            if (response.ok) {
                const botMessage = await response.json();
                sendOutputMessage(botMessage.answer);
                chatbox.scrollTop = chatbox.scrollHeight;
            } else {
                console.error('Error fetching the answer:', response.statusText);
                sendOutputMessage('Sorry, something went wrong.');
            }
        } catch (error) {
            console.error('Error fetching the answer:', error);
            sendOutputMessage('Sorry, something went wrong.');
        }
    }
}

/**
 * Displays user message in chat
 * @param {string} userMessage - Message from user
 */
 async function sendInputMessage(userMessage) {
    if (!userMessage) {
        userMessage = chatLine.value.trim();
    }

    let newMessage = document.createElement("li");
    newMessage.classList.add("chat", "incoming");

    const icon = document.createElement("span");
    icon.classList.add("material-symbols-outlined");
    icon.textContent = "person";
    newMessage.appendChild(icon);

    let messageContainer = document.createElement("div");
    messageContainer.classList.add("message-container");

    let messageText = document.createElement("p");
    messageText.classList.add("message-text");
    messageText.textContent = userMessage;
    messageContainer.appendChild(messageText);

    newMessage.appendChild(messageContainer);

    if (uploadedFile) {
        const previewContainerClone = previewContainer.cloneNode(true);
        previewContainerClone.removeAttribute('id');
        const removeButton = previewContainerClone.querySelector('.remove-button');

        if (removeButton) {
            removeButton.remove();
        }

        newMessage.appendChild(previewContainerClone);
    }

    chatbox.appendChild(newMessage);

    chatLine.value = "";
    chatLine.style.height = 'auto';
    uploadedFile = null;
    previewContainer.innerHTML = "";
    chatbox.scrollTop = chatbox.scrollHeight;
}

/**
 * Displays bot message in chat
 * @param {string} outputMessage - Message from bot
 */
async function sendOutputMessage(outputMessage) {
    let newOutputMessage = document.createElement("li");
    newOutputMessage.classList.add("chat", "outgoing");

    const icon = document.createElement("span");
    icon.classList.add("material-symbols-outlined");
    icon.textContent = "smart_toy";

    let messageContainer = document.createElement("div");
    messageContainer.classList.add("message-container");

    const rawHtml = marked.parse(outputMessage);
    messageContainer.innerHTML = DOMPurify.sanitize(rawHtml);

    newOutputMessage.appendChild(icon);
    newOutputMessage.appendChild(messageContainer);

    chatbox.appendChild(newOutputMessage);

    const codeBlocks = newOutputMessage.querySelectorAll('pre code');
    codeBlocks.forEach(block => {
        hljs.highlightElement(block);
    });

    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(messageContainer, {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '\\[', right: '\\]', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\(', right: '\\)', display: false}
            ],
            ignore: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'kbd', 'tt']
        });
    } else {
        console.warn("KaTeX auto-render extension not loaded, math formulas may not render.");
    }

}
/**
 * Kiwi Widget Configuration - Shadow DOM Compatible
 * Contains shared configuration and DOM element references
 */

// Helper functions for Shadow DOM compatibility
const getContext = () => window.KIWI_WIDGET_CONTEXT || { 
    shadowRoot: document, 
    baseUrl: window.BASE_URL,
    querySelector: (selector) => document.querySelector(selector),
    querySelectorAll: (selector) => document.querySelectorAll(selector),
    getElementById: (id) => document.getElementById(id)
};

// Domain configuration
const domain = getContext().baseUrl || window.BASE_URL;

// DOM Elements - using Shadow DOM safe selectors
const chatWidget = getContext().getElementById('chat-widget');
const widgetToggler = getContext().getElementById('widget-toggler');
const fileInput = getContext().getElementById('file-input');
const fileUpload = getContext().getElementById('file-upload');
const selectionBox = getContext().getElementById('selection-box');
const sendButton = getContext().getElementById("send-button");
const chatbox = getContext().querySelector('.chatbox');
const chatLine = getContext().querySelector('.chat-textarea');
const resizeHandles = getContext().querySelectorAll('.resize-handle');
const previewContainer = getContext().getElementById('preview-container');
const textarea = getContext().getElementById('chat-textarea');
const chatInput = getContext().getElementById('chat-input');
const menuButton = getContext().getElementById('menu-button');
const websearchButton = getContext().getElementById('globe-button');
const dropdownMenu = getContext().querySelector('.menu');
const clearButton = getContext().getElementById('clear-button');
const welcomeMessage = getContext().getElementById('welcome_message');
let chatBotName = getContext().getElementById('chatbot_name');
const selectedCollection = getContext().getElementById('selected_collection');
const menuList = getContext().getElementById('menuList');
const keyInputWrapper = getContext().getElementById("keyInputWrapper");
const keyInput = getContext().getElementById("keyInput");
const keySubmit = getContext().getElementById("key-submit");
const infoButton = getContext().getElementById('info-button');
const selected = getContext().getElementById("dropdownSelected");
const optionsContainer = getContext().getElementById("dropdownOptions");

// State variables
let uploadedFile = null;
let collection = "Basiswissen";
let desktopStream = null;
let isProcessing = false;

// Configure Marked.js options
marked.setOptions({
    highlight: (code, lang) => {
        const language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
    },
    langPrefix: 'hljs language-',
    gfm: true
});

// Configure MathJax
window.MathJax = {
    tex: { inlineMath: [['$', '$'], ['\\(', '\\)']] },
    svg: { fontCache: 'global' }
};

// Export the configuration
const config = {
    domain,
    elements: {
        chatWidget,
        widgetToggler,
        fileInput,
        fileUpload,
        selectionBox,
        sendButton,
        chatbox,
        chatLine,
        resizeHandles,
        previewContainer,
        textarea,
        chatInput,
        menuButton,
        websearchButton,
        dropdownMenu,
        clearButton,
        welcomeMessage,
        chatBotName,
        selectedCollection,
        menuList,
        keyInputWrapper,
        keyInput,
        keySubmit,
        infoButton,
        selected,
        optionsContainer
    },
    state: {
        uploadedFile,
        collection,
        desktopStream,
        isProcessing
    }
};
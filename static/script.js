// Complete Mobile-Optimized script.js for AlexAI Assistant with Enhanced Validation

// --- Global Variables ---
let isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
let isTouch = 'ontouchstart' in window;
let abortController;
let isGenerating = false;
let attachedImageFile = null;
let isTtsEnabled = false;
let emotionHistory = [];
let proactiveSuggestions = [];
let isListening = false;
let recognition = null;

// --- Validation Global Variables ---
let validationPopup = null;
let validationTimeouts = {};

// --- DOM Elements (will be initialized on DOMContentLoaded) ---
let conversationIdInput, chatForm, userInput, chatBox, stopButtonContainer, stopButton;
let attachButton, imageUploadInput, imagePreviewContainer, imagePreview, removeImageButton;
let themeToggle, themeIcon, ttsToggle, ttsIcon, clearChatButton, micButton, thinkingIndicator;

// --- Enhanced Form Validation Functions ---
function createValidationPopup() {
    if (validationPopup) return validationPopup;

    validationPopup = document.createElement('div');
    validationPopup.className = 'validation-popup';
    validationPopup.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #ff4444;
        color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        z-index: 10000;
        max-width: 300px;
        text-align: center;
        font-family: Arial, sans-serif;
        display: none;
        animation: popupSlide 0.3s ease-out;
    `;

    // Add CSS animation keyframes
    const style = document.createElement('style');
    style.textContent = `
        @keyframes popupSlide {
            from {
                opacity: 0;
                transform: translate(-50%, -60%);
            }
            to {
                opacity: 1;
                transform: translate(-50%, -50%);
            }
        }
        
        .validation-popup {
            font-size: 14px;
            line-height: 1.4;
        }
        
        .validation-icon {
            font-size: 24px;
            margin-bottom: 10px;
        }
        
        .validation-message {
            margin-bottom: 15px;
            font-weight: 500;
        }
        
        .validation-close {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s ease;
        }
        
        .validation-close:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .inline-error {
            color: #ff4444;
            font-size: 12px;
            margin-top: 5px;
            padding: 5px;
            background: rgba(255, 68, 68, 0.1);
            border-radius: 4px;
            border-left: 3px solid #ff4444;
            animation: errorSlide 0.3s ease-out;
        }
        
        @keyframes errorSlide {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @media (max-width: 768px) {
            .validation-popup {
                max-width: 90%;
                padding: 15px;
                font-size: 16px;
            }
            
            .validation-close {
                padding: 12px 20px;
                font-size: 16px;
            }
        }
    `;
    document.head.appendChild(style);

    document.body.appendChild(validationPopup);
    return validationPopup;
}

function showValidationError(message, targetElement = null) {
    const popup = createValidationPopup();
    popup.innerHTML = `
        <div class="validation-icon">⚠️</div>
        <div class="validation-message">${message}</div>
        <button class="validation-close" onclick="hideValidationError()">OK</button>
    `;

    popup.style.display = 'block';

    // Add haptic feedback on mobile
    if (navigator.vibrate && isMobile) {
        navigator.vibrate([100, 50, 100]);
    }

    // Highlight the problematic field
    if (targetElement) {
        targetElement.style.borderColor = '#ff4444';
        targetElement.style.boxShadow = '0 0 5px rgba(255, 68, 68, 0.5)';

        // Remove highlight after 3 seconds
        setTimeout(() => {
            targetElement.style.borderColor = '';
            targetElement.style.boxShadow = '';
        }, 3000);
    }

    // Auto-hide after 5 seconds
    setTimeout(() => {
        hideValidationError();
    }, 5000);
}

function hideValidationError() {
    if (validationPopup) {
        validationPopup.style.display = 'none';
    }
}

// Real-time validation with server
async function validateFieldWithServer(fieldName, fieldValue, fieldElement) {
    try {
        const response = await fetch('/api/validate/field', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                field: fieldName,
                value: fieldValue
            })
        });

        const data = await response.json();

        if (!data.valid && data.errors.length > 0) {
            showInlineError(fieldElement, data.errors[0].message);
            return false;
        } else {
            clearFieldError(fieldElement);
            return true;
        }
    } catch (error) {
        console.error('Validation error:', error);
        return true; // Don't block on network errors
    }
}

function showInlineError(element, message) {
    // Remove existing error message
    const existingError = element.parentNode.querySelector('.inline-error');
    if (existingError) {
        existingError.remove();
    }

    // Create new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'inline-error';
    errorDiv.textContent = message;

    // Insert after the input field
    element.parentNode.insertBefore(errorDiv, element.nextSibling);

    // Highlight the field
    element.style.borderColor = '#ff4444';
    element.style.backgroundColor = 'rgba(255, 68, 68, 0.05)';

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
        element.style.borderColor = '';
        element.style.backgroundColor = '';
    }, 5000);
}

function clearFieldError(field) {
    const existingError = field.parentNode.querySelector('.inline-error');
    if (existingError) {
        existingError.remove();
    }
    field.style.borderColor = '';
    field.style.backgroundColor = '';
    field.style.boxShadow = '';
}

function clearValidationErrors(form) {
    // Remove all inline errors
    form.querySelectorAll('.inline-error').forEach(error => error.remove());

    // Reset field styles
    form.querySelectorAll('input').forEach(input => {
        input.style.borderColor = '';
        input.style.backgroundColor = '';
        input.style.boxShadow = '';
    });

    // Hide popup
    hideValidationError();
}

// Enhanced login form validation
function setupLoginValidation() {
    const loginForm = document.getElementById('login-form');
    const usernameField = document.getElementById('username');
    const passwordField = document.getElementById('password');

    if (loginForm && usernameField && passwordField) {
        // Real-time validation with debouncing
        usernameField.addEventListener('input', () => {
            clearTimeout(validationTimeouts.username);
            validationTimeouts.username = setTimeout(() => {
                const username = usernameField.value.trim();
                if (username.length > 0) {
                    validateFieldWithServer('username', username, usernameField);
                } else {
                    clearFieldError(usernameField);
                }
            }, 500);
        });

        passwordField.addEventListener('input', () => {
            clearTimeout(validationTimeouts.password);
            validationTimeouts.password = setTimeout(() => {
                const password = passwordField.value;
                if (password.length > 0) {
                    validateFieldWithServer('password', password, passwordField);
                } else {
                    clearFieldError(passwordField);
                }
            }, 500);
        });

        // Form submission with enhanced validation
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = usernameField.value.trim();
            const password = passwordField.value;

            // Clear previous errors
            clearValidationErrors(loginForm);

            // Client-side validation first
            if (!username) {
                showValidationError('Username is required!', usernameField);
                usernameField.focus();
                return;
            }

            if (!password) {
                showValidationError('Password is required!', passwordField);
                passwordField.focus();
                return;
            }

            // Submit to server
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (data.success) {
                    // Success - redirect
                    window.location.href = data.redirect;
                } else {
                    // Handle validation errors
                    if (data.errors) {
                        data.errors.forEach(error => {
                            const field = error.field === 'username' ? usernameField : passwordField;
                            showInlineError(field, error.message);
                        });
                    } else {
                        showValidationError(data.message || 'Login failed');
                    }
                }
            } catch (error) {
                console.error('Login error:', error);
                showValidationError('Network error. Please check your connection and try again.');
            }
        });
    }
}

// Enhanced registration form validation
function setupRegistrationValidation() {
    const registerForm = document.getElementById('register-form');
    const usernameField = document.getElementById('username');
    const passwordField = document.getElementById('password');

    if (registerForm && usernameField && passwordField) {
        // Real-time validation with debouncing
        usernameField.addEventListener('input', () => {
            clearTimeout(validationTimeouts.regUsername);
            validationTimeouts.regUsername = setTimeout(() => {
                const username = usernameField.value.trim();
                if (username.length > 0) {
                    validateFieldWithServer('username', username, usernameField);
                } else {
                    clearFieldError(usernameField);
                }
            }, 500);
        });

        passwordField.addEventListener('input', () => {
            clearTimeout(validationTimeouts.regPassword);
            validationTimeouts.regPassword = setTimeout(() => {
                const password = passwordField.value;
                if (password.length > 0) {
                    validateFieldWithServer('password', password, passwordField);
                } else {
                    clearFieldError(passwordField);
                }
            }, 500);
        });

        // Form submission
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = usernameField.value.trim();
            const password = passwordField.value;

            // Clear previous errors
            clearValidationErrors(registerForm);

            // Submit to server
            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (data.success) {
                    // Success - show success message and redirect
                    const popup = createValidationPopup();
                    popup.innerHTML = `
                        <div class="validation-icon">✅</div>
                        <div class="validation-message">Registration successful! Redirecting to login...</div>
                    `;
                    popup.style.background = '#44ff44';
                    popup.style.display = 'block';

                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 2000);
                } else {
                    // Handle validation errors
                    if (data.errors) {
                        data.errors.forEach(error => {
                            const field = error.field === 'username' ? usernameField : passwordField;
                            showInlineError(field, error.message);
                        });
                    } else {
                        showValidationError(data.message || 'Registration failed');
                    }
                }
            } catch (error) {
                console.error('Registration error:', error);
                showValidationError('Network error. Please check your connection and try again.');
            }
        });
    }
}

// --- Mobile-Specific Functions ---
function initializeMobileMenu() {
    // Only create mobile menu if it doesn't exist
    if (document.querySelector('.mobile-menu-toggle')) return;

    const mobileToggle = document.createElement('button');
    mobileToggle.className = 'mobile-menu-toggle';
    mobileToggle.innerHTML = '☰';
    mobileToggle.setAttribute('aria-label', 'Toggle menu');
    document.body.appendChild(mobileToggle);

    const sidebar = document.querySelector('.sidebar');
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);

    function toggleSidebar() {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('show');
        mobileToggle.innerHTML = sidebar.classList.contains('open') ? '✕' : '☰';
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
        mobileToggle.innerHTML = '☰';
    }

    mobileToggle.addEventListener('click', toggleSidebar);
    overlay.addEventListener('click', closeSidebar);

    // Close sidebar when clicking on conversation items
    document.querySelectorAll('.conversation-item').forEach(item => {
        item.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                closeSidebar();
            }
        });
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            closeSidebar();
        }
    });
}

function enhanceTouchExperience() {
    // Prevent double-tap zoom on buttons
    document.querySelectorAll('button, .control-button, .conversation-item').forEach(element => {
        element.addEventListener('touchend', function(e) {
            e.preventDefault();
            this.click();
        }, { passive: false });
    });

    // Improve scroll behavior on mobile
    if (isMobile) {
        document.body.style.overflow = 'hidden';

        // Add momentum scrolling to chat box
        if (chatBox) {
            chatBox.style.webkitOverflowScrolling = 'touch';
        }
    }
}

function handleMobileKeyboard() {
    if (isMobile && userInput) {
        // Handle virtual keyboard on mobile
        userInput.addEventListener('focus', () => {
            setTimeout(() => {
                userInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 300);
        });

        // Auto-resize textarea on mobile
        userInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        // Handle Enter key on mobile
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (chatForm) {
                    chatForm.dispatchEvent(new Event('submit'));
                }
            }
        });
    }
}

function enhanceMobileThemeToggle() {
    if (themeToggle) {
        // Add haptic feedback for theme toggle on mobile
        themeToggle.addEventListener('click', () => {
            if (navigator.vibrate && isMobile) {
                navigator.vibrate(50);
            }
        });
    }
}

// --- Speech Recognition Functions ---
function initializeSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isListening = true;
            if (micButton) {
                micButton.textContent = '🎤';
                micButton.style.background = '#ff4444';
                micButton.style.color = 'white';

                // Add haptic feedback on mobile
                if (navigator.vibrate && isMobile) {
                    navigator.vibrate(100);
                }
            }
            userInput.value = '';
            userInput.placeholder = 'Listening...';
            addListeningIndicator();
        };

        recognition.onend = () => {
            isListening = false;
            if (micButton) {
                micButton.textContent = '🎙️';
                micButton.style.background = '';
                micButton.style.color = '';
            }
            userInput.placeholder = 'Type your message...';
            removeListeningIndicator();
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;

            // Auto-submit after a short delay
            setTimeout(() => {
                if (transcript.trim() && !isGenerating) {
                    if (chatForm) {
                        chatForm.dispatchEvent(new Event('submit'));
                    }
                }
            }, 500);
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            isListening = false;
            if (micButton) {
                micButton.textContent = '🎙️';
                micButton.style.background = '';
                micButton.style.color = '';
            }

            // Mobile-specific error messages
            if (isMobile) {
                userInput.placeholder = 'Voice not available. Try typing.';
            } else {
                userInput.placeholder = 'Speech error. Try again.';
            }

            removeListeningIndicator();

            setTimeout(() => {
                userInput.placeholder = 'Type your message...';
            }, 3000);
        };
    }
}

// --- Helper Functions ---
const speak = (text) => {
    if (isTtsEnabled && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text.replace(/[*`#_]/g, ''));
        utterance.rate = 0.9;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
    }
};

function addListeningIndicator() {
    removeListeningIndicator();
    const speechIndicator = document.createElement('div');
    speechIndicator.id = 'speech-indicator';
    speechIndicator.className = 'speech-indicator';
    speechIndicator.innerHTML = '🎤 Listening...';
    chatBox.appendChild(speechIndicator);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function removeListeningIndicator() {
    const indicator = document.getElementById('speech-indicator');
    if (indicator) {
        indicator.remove();
    }
}

function addMessageToUI(content, type) {
    const messageElement = document.createElement("div");
    messageElement.classList.add("message", type);
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (type === 'bot-message') {
        contentDiv.innerHTML = md.render(content || "");
    } else {
        contentDiv.textContent = content;
    }

    messageElement.appendChild(contentDiv);
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
    return messageElement;
}

function updateUserMessageWithSentiment(element, sentiment) {
    const sentimentDiv = document.createElement('div');
    sentimentDiv.className = 'sentiment-indicator';
    sentimentDiv.innerHTML = `
        <span class="sentiment-label">Sentiment:</span>
        <span class="sentiment-positive">Positive: ${(sentiment.positive * 100).toFixed(1)}%</span>
        <span class="sentiment-neutral">Neutral: ${(sentiment.neutral * 100).toFixed(1)}%</span>
        <span class="sentiment-negative">Negative: ${(sentiment.negative * 100).toFixed(1)}%</span>
    `;
    element.appendChild(sentimentDiv);
}

function addCopyButtons() {
    document.querySelectorAll('pre code').forEach(block => {
        if (!block.parentElement.querySelector('.copy-button')) {
            const copyButton = document.createElement('button');
            copyButton.className = 'copy-button';
            copyButton.textContent = 'Copy';
            copyButton.onclick = () => {
                navigator.clipboard.writeText(block.textContent);
                copyButton.textContent = 'Copied!';
                setTimeout(() => copyButton.textContent = 'Copy', 2000);
            };
            block.parentElement.style.position = 'relative';
            block.parentElement.appendChild(copyButton);
        }
    });
}

// --- Advanced Feature Handlers ---
function handleSpecialEvents(eventType, data) {
    switch(eventType) {
        case 'emotion':
            displayEmotionIndicator(data);
            emotionHistory.push({...data, timestamp: Date.now()});
            if (emotionHistory.length > 10) {
                emotionHistory.shift();
            }
            break;
        case 'automation':
            displayAutomationResults(data);
            break;
        case 'proactive':
            displayProactiveSuggestions(data);
            proactiveSuggestions = data;
            break;
    }
}

function displayEmotionIndicator(emotions) {
    const emotionDiv = document.createElement('div');
    emotionDiv.className = 'emotion-indicator';

    const dominantEmotion = Object.keys(emotions).reduce((a, b) =>
        emotions[a] > emotions[b] ? a : b
    );

    const emotionEmoji = {
        'happiness': '😊',
        'stress': '😰',
        'neutral': '😐'
    };

    emotionDiv.innerHTML = `
        <span class="emotion-badge ${dominantEmotion}">
            ${emotionEmoji[dominantEmotion]} ${dominantEmotion} (${(emotions[dominantEmotion] * 100).toFixed(0)}%)
        </span>
    `;

    chatBox.appendChild(emotionDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function displayAutomationResults(results) {
    const automationDiv = document.createElement('div');
    automationDiv.className = 'automation-results';

    let content = '<div class="automation-header">🤖 Automated Actions:</div>';
    results.forEach(result => {
        content += `<div class="automation-item">${result.message}</div>`;
    });

    automationDiv.innerHTML = content;
    chatBox.appendChild(automationDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function displayProactiveSuggestions(suggestions) {
    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'proactive-suggestions';

    let content = '<div class="suggestions-header">💡 Suggestions:</div>';
    suggestions.forEach((suggestion, index) => {
        content += `
            <div class="suggestion-item" onclick="acceptSuggestion('${suggestion.type}', ${index})">
                ${suggestion.message}
            </div>
        `;
    });

    suggestionsDiv.innerHTML = content;
    chatBox.appendChild(suggestionsDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function acceptSuggestion(suggestionType, index) {
    const suggestion = proactiveSuggestions[index];
    if (suggestion && suggestion.actions) {
        userInput.value = `Please help me with ${suggestionType}: ${suggestion.message}`;
    } else {
        userInput.value = `I'd like help with ${suggestionType}`;
    }

    // Remove the suggestion after acceptance
    document.querySelectorAll('.proactive-suggestions').forEach(el => el.remove());

    // Trigger form submission
    if (chatForm) {
        chatForm.dispatchEvent(new Event('submit'));
    }
}

// --- Logout Functions ---
function setupLogoutConfirmation() {
    const logoutButtons = document.querySelectorAll('.logout-button, .logout-control, a[href*="logout"]');

    logoutButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();

            // Add haptic feedback on mobile
            if (navigator.vibrate && isMobile) {
                navigator.vibrate(100);
            }

            if (confirm('Are you sure you want to logout? Any unsaved work will be lost.')) {
                localStorage.removeItem('theme');
                localStorage.removeItem('ttsEnabled');
                emotionHistory = [];
                proactiveSuggestions = [];

                if (chatBox) {
                    chatBox.innerHTML = '<div class="welcome-message">Logging out... Please wait.</div>';
                }

                setTimeout(() => {
                    window.location.href = button.href || '/logout';
                }, 500);
            }
        });
    });
}

function performLogout(skipConfirmation = false) {
    if (!skipConfirmation && !confirm('Are you sure you want to logout?')) {
        return false;
    }

    localStorage.clear();
    emotionHistory = [];
    proactiveSuggestions = [];

    if (abortController) {
        abortController.abort();
    }

    isGenerating = false;
    isListening = false;

    window.location.href = '/logout';
    return true;
}

// --- Event Listener Setup ---
function setupEventListeners() {
    // Theme toggle with proper logic
    if (themeToggle && themeIcon) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('light-theme');
            const isLight = document.body.classList.contains('light-theme');
            themeIcon.textContent = isLight ? '🌙' : '☀️';
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
        });
    }

    // TTS toggle
    if (ttsToggle) {
        ttsToggle.addEventListener('click', () => {
            isTtsEnabled = !isTtsEnabled;
            ttsIcon.textContent = isTtsEnabled ? '🔊' : '🔇';
            localStorage.setItem('ttsEnabled', isTtsEnabled);
        });
    }

    // Microphone button
    if (micButton) {
        micButton.addEventListener('click', () => {
            if (!recognition) {
                showValidationError('Speech recognition not supported in this browser.');
                return;
            }

            if (isListening) {
                recognition.stop();
            } else {
                if (!isGenerating) {
                    recognition.start();
                } else {
                    showValidationError('Please wait for the current response to complete.');
                }
            }
        });
    }

    // Image attachment
    if (attachButton && imageUploadInput) {
        attachButton.addEventListener('click', () => {
            imageUploadInput.click();
        });

        imageUploadInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                if (!file.type.startsWith('image/')) {
                    showValidationError('Please select a valid image file.');
                    return;
                }

                if (file.size > 5 * 1024 * 1024) {
                    showValidationError('Image file too large. Please select an image under 5MB.');
                    return;
                }

                attachedImageFile = file;
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.src = e.target.result;
                    imagePreviewContainer.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Remove image
    if (removeImageButton) {
        removeImageButton.addEventListener('click', () => {
            attachedImageFile = null;
            imagePreviewContainer.style.display = 'none';
            imageUploadInput.value = '';
        });
    }

    // Stop generation
    if (stopButton) {
        stopButton.addEventListener('click', () => {
            if (abortController) {
                abortController.abort();
            }
            isGenerating = false;
            stopButtonContainer.style.display = 'none';
            chatForm.style.display = 'flex';
            thinkingIndicator.style.display = 'none';
        });
    }

    // Setup logout confirmation
    setupLogoutConfirmation();

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + Enter to send message
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && userInput === document.activeElement) {
            e.preventDefault();
            if (chatForm) {
                chatForm.dispatchEvent(new Event('submit'));
            }
        }

        // Escape to stop generation
        if (e.key === 'Escape' && isGenerating) {
            e.preventDefault();
            if (stopButton) {
                stopButton.click();
            }
        }

        // Ctrl+Shift+L for quick logout
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'L') {
            e.preventDefault();
            performLogout();
        }
    });

    // Chat form submission
    if (chatForm) {
        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            if (isGenerating) return;

            const prompt = userInput.value.trim();
            if (!prompt && !attachedImageFile) return;

            isGenerating = true;
            abortController = new AbortController();

            // UI updates
            chatForm.style.display = 'none';
            stopButtonContainer.style.display = 'flex';
            thinkingIndicator.style.display = 'block';

            // Add user message to UI
            const userMessageElement = addMessageToUI(prompt, 'user-message');
            userInput.value = '';

            // Prepare form data
            const formData = new FormData();
            formData.append('prompt', prompt);
            formData.append('conversation_id', conversationIdInput.value);
            if (attachedImageFile) {
                formData.append('image', attachedImageFile);
            }

            let botMessageElement = null;
            let fullResponse = '';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    body: formData,
                    signal: abortController.signal
                });

                if (!response.ok) {
                    if (response.status === 401 || response.status === 403) {
                        showValidationError('Your session has expired. Please log in again.');
                        setTimeout(() => {
                            performLogout(true);
                        }, 2000);
                        return;
                    }
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');

                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i];

                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.text) {
                                    fullResponse += data.text;
                                    if (!botMessageElement) {
                                        botMessageElement = addMessageToUI('', 'bot-message');
                                    }
                                    const contentDiv = botMessageElement.querySelector('.message-content');
                                    contentDiv.innerHTML = md.render(fullResponse);
                                    chatBox.scrollTop = chatBox.scrollHeight;
                                }
                                if (data.error) {
                                    throw new Error(data.error);
                                }
                            } catch (parseError) {
                                console.error('Error parsing JSON:', parseError);
                            }
                        } else if (line.startsWith('event: ')) {
                            const eventType = line.slice(7);
                            const nextLine = lines[i + 1];
                            if (nextLine && nextLine.startsWith('data: ')) {
                                try {
                                    const eventData = JSON.parse(nextLine.slice(6));

                                    if (eventType === 'sentiment') {
                                        updateUserMessageWithSentiment(userMessageElement, eventData);
                                    } else if (eventType === 'error') {
                                        throw new Error(eventData.error);
                                    } else {
                                        handleSpecialEvents(eventType, eventData);
                                    }
                                    i++;
                                } catch (parseError) {
                                    console.error(`Error parsing ${eventType} data:`, parseError);
                                }
                            }
                        }
                    }
                }
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error('Chat error:', error);
                    if (!botMessageElement) {
                        addMessageToUI('Sorry, an error occurred. Please try again.', 'bot-message');
                    }
                }
            } finally {
                isGenerating = false;
                stopButtonContainer.style.display = 'none';
                chatForm.style.display = 'flex';
                thinkingIndicator.style.display = 'none';
                userInput.focus();

                // Clear image attachment
                if (removeImageButton) {
                    removeImageButton.click();
                }

                if (fullResponse.trim() && !abortController.signal.aborted) {
                    addCopyButtons();
                    speak(fullResponse);
                }
            }
        });
    }
}

// --- Page Initialization ---
function initializePage() {
    // Initialize Markdown renderer
    window.md = window.markdownit({
        highlight: (str, lang) => {
            if (lang && hljs.getLanguage(lang)) {
                try {
                    return '<pre><code class="hljs language-' + lang + '">' +
                           hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
                           '</code></pre>';
                } catch (__) {}
            }
            return '<pre><code class="hljs">' + md.utils.escapeHtml(str) + '</code></pre>';
        }
    });

    // Load saved theme preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        if (themeIcon) themeIcon.textContent = '🌙';
    } else {
        document.body.classList.remove('light-theme');
        if (themeIcon) themeIcon.textContent = '☀️';
    }

    // Load TTS preference
    const savedTts = localStorage.getItem('ttsEnabled');
    if (savedTts === 'true') {
        isTtsEnabled = true;
        if (ttsIcon) ttsIcon.textContent = '🔊';
    }

    // Initialize speech recognition
    initializeSpeechRecognition();

    // Process existing bot messages
    document.querySelectorAll('.bot-message .message-content').forEach(el => {
        const rawMarkdown = el.textContent;
        el.innerHTML = md.render(rawMarkdown);
    });

    addCopyButtons();
    chatBox.scrollTop = chatBox.scrollHeight;

    // Focus on input
    if (userInput) {
        userInput.focus();
    }
}

// --- Main Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    // Initialize DOM elements
    conversationIdInput = document.getElementById("conversation-id");
    chatForm = document.getElementById("chat-form");
    userInput = document.getElementById("user-input");
    chatBox = document.getElementById("chat-box");
    stopButtonContainer = document.getElementById("stop-button-container");
    stopButton = document.getElementById("stop-button");
    attachButton = document.getElementById("attach-button");
    imageUploadInput = document.getElementById("image-upload-input");
    imagePreviewContainer = document.getElementById("image-preview-container");
    imagePreview = document.getElementById("image-preview");
    removeImageButton = document.getElementById("remove-image-button");
    themeToggle = document.getElementById("theme-toggle");
    themeIcon = document.getElementById("theme-icon");
    ttsToggle = document.getElementById("tts-toggle");
    ttsIcon = document.getElementById("tts-icon");
    clearChatButton = document.getElementById("clear-chat-button");
    micButton = document.getElementById("mic-button");
    thinkingIndicator = document.getElementById("thinking-indicator");

    // Initialize mobile features
    initializeMobileMenu();
    enhanceTouchExperience();
    handleMobileKeyboard();
    enhanceMobileThemeToggle();

    // Add mobile-specific classes
    if (isMobile) {
        document.body.classList.add('mobile-device');
    }
    if (isTouch) {
        document.body.classList.add('touch-device');
    }

    // Prevent zoom on input focus (iOS)
    if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
        const viewport = document.querySelector('meta[name=viewport]');
        if (viewport) {
            viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
        }
    }

    // Initialize page and setup event listeners
    initializePage();
    setupEventListeners();

    // Setup form validation
    setupLoginValidation();
    setupRegistrationValidation();

    // Expose logout function globally
    window.performLogout = performLogout;
});

// Make functions globally available
window.acceptSuggestion = acceptSuggestion;
window.hideValidationError = hideValidationError;
window.showValidationError = showValidationError;

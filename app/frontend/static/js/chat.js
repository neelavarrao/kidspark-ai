document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const userNameElement = document.getElementById('user-name');
    const logoutBtn = document.getElementById('logout-btn');

    // Check if user is logged in
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')) : null;

    if (!token || !userData) {
        window.location.href = '/';
        return;
    }

    // Display user name
    userNameElement.textContent = userData.name;

    // Handle logout
    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/';
    });

    // Load chat history
    loadChatHistory();

    // Handle message sending
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const content = messageInput.value.trim();
        if (!content) return;

        // Clear input
        messageInput.value = '';

        // Add user message to UI
        appendMessage(content, 'user');

        try {
            // Use the new agent endpoint
            const response = await fetch('/api/chat/agent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    content: content,
                    user_id: userData.id
                })
            });

            if (!response.ok) {
                throw new Error('Failed to send message');
            }

            // Get AI response
            const data = await response.json();

            // Add AI response to UI with intent badge
            appendMessageWithIntent(data.content, 'assistant', data.detected_intent, data.metadata);

        } catch (error) {
            console.error('Error:', error);
            appendErrorMessage('Failed to send message. Please try again.');
        }
    });

    // Helper to append message to chat
    function appendMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const messagePara = document.createElement('p');
        messagePara.textContent = content;

        messageContent.appendChild(messagePara);
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Helper to append message with intent badge
    function appendMessageWithIntent(content, sender, intent, metadata = null) {
        console.log('appendMessageWithIntent called:', { content, sender, intent, metadata });
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        // Split content to remove the debug intent info
        const contentParts = content.split('[Intent detected:');
        const mainContent = contentParts[0].trim();

        const messagePara = document.createElement('p');
        messagePara.textContent = mainContent;
        messageContent.appendChild(messagePara);

        // Check if this is a story response that should trigger the story modal
        if (intent === 'story' && metadata && metadata.display_type === 'story' && metadata.story_data) {
            // Add a clickable button to open the story
            const storyButton = document.createElement('button');
            storyButton.className = 'btn-primary';
            storyButton.style.marginTop = '10px';
            storyButton.textContent = 'Open Story';
            storyButton.addEventListener('click', () => {
                // Dispatch event to open story modal
                document.dispatchEvent(
                    new CustomEvent('storyReceived', {
                        detail: metadata.story_data
                    })
                );
            });
            messageContent.appendChild(storyButton);
        }

        // Check if this is an activity response that should trigger the activity modal
        console.log('Checking activity response:', intent, metadata);
        if (intent === 'activity' && metadata && metadata.display_type === 'activity' && metadata.activity_data) {
            console.log('Adding activity button, activity_data:', metadata.activity_data);
            // Add a clickable button to open the activity
            const activityButton = document.createElement('button');
            activityButton.className = 'btn-primary';
            activityButton.style.marginTop = '10px';
            activityButton.style.backgroundColor = '#4CAF50'; // Green for activities
            activityButton.style.display = 'inline-block';
            activityButton.style.width = 'auto';
            activityButton.textContent = 'View Activity';
            activityButton.addEventListener('click', () => {
                // Dispatch event to open activity modal
                document.dispatchEvent(
                    new CustomEvent('activityReceived', {
                        detail: metadata.activity_data
                    })
                );
            });
            messageContent.appendChild(activityButton);
            console.log('Activity button added to messageContent');
        }

        // Add intent badge if available
        if (intent) {
            const intentBadge = document.createElement('div');
            intentBadge.className = 'intent-badge';

            // Set badge color based on intent type
            let badgeColor = '';
            switch(intent) {
                case 'activity':
                    badgeColor = '#4CAF50'; // Green
                    break;
                case 'story':
                    badgeColor = '#2196F3'; // Blue
                    break;
                case 'why':
                    badgeColor = '#FF9800'; // Orange
                    break;
                case 'greeting':
                    badgeColor = '#9C27B0'; // Purple
                    break;
                default:
                    badgeColor = '#757575'; // Grey
            }

            intentBadge.style.backgroundColor = badgeColor;
            intentBadge.textContent = intent;

            // Add confidence if available
            if (metadata && metadata.confidence) {
                const confidence = Math.round(metadata.confidence * 100);
                intentBadge.textContent += ` (${confidence}%)`;
            }

            messageContent.appendChild(intentBadge);
        }

        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);

        // If this is a story response, automatically trigger the story modal
        if (intent === 'story' && metadata && metadata.display_type === 'story' && metadata.story_data) {
            // Delay slightly to ensure UI updates first
            setTimeout(() => {
                document.dispatchEvent(
                    new CustomEvent('storyReceived', {
                        detail: metadata.story_data
                    })
                );
            }, 500);
        }

        // If this is an activity response, automatically trigger the activity modal
        if (intent === 'activity' && metadata && metadata.display_type === 'activity' && metadata.activity_data) {
            // Delay slightly to ensure UI updates first
            setTimeout(() => {
                document.dispatchEvent(
                    new CustomEvent('activityReceived', {
                        detail: metadata.activity_data
                    })
                );
            }, 500);
        }

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Helper to append error message
    function appendErrorMessage(errorText) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.display = 'block';
        errorDiv.textContent = errorText;
        chatMessages.appendChild(errorDiv);

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Load chat history from server
    async function loadChatHistory() {
        try {
            const response = await fetch('/api/chat/messages/history', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load chat history');
            }

            const messages = await response.json();

            // Clear default welcome message
            chatMessages.innerHTML = '';

            // Add welcome message for the agent system
            const welcomeMessage = {
                content: "Welcome to KidSpark AI! I'm your intelligent parenting assistant. I can help with:\n\n• Activity suggestions for your children\n• Bedtime stories personalized for your child\n• Answers to all those curious 'Why?' questions\n\nWhat would you like help with today?",
                sender: "assistant"
            };

            appendMessage(welcomeMessage.content, welcomeMessage.sender);

            // Add messages to UI (legacy messages without intent)
            messages.forEach(message => {
                appendMessage(message.content, message.sender);
            });

        } catch (error) {
            console.error('Error:', error);
            appendErrorMessage('Failed to load chat history. Please refresh the page.');
        }
    }
});
document.addEventListener('DOMContentLoaded', () => {
    const whyForm = document.getElementById('why-form');
    const whyInput = document.getElementById('why-input');
    const whyMessages = document.getElementById('why-messages');
    const ageSelect = document.getElementById('age-select');
    const userNameElement = document.getElementById('user-name');
    const logoutBtn = document.getElementById('logout-btn');

    // Session state
    let sessionId = null;
    let lastQuestion = null;

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

    // Handle question submission
    whyForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const question = whyInput.value.trim();
        if (!question) return;

        // Clear input
        whyInput.value = '';

        // Add question to UI
        appendQuestion(question);

        // Show loading
        showLoading();

        // Send to API
        await askQuestion(question, false);
    });

    // Ask a question
    async function askQuestion(question, isFollowUp) {
        try {
            const response = await fetch('/api/why', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    question: question,
                    age_group: ageSelect.value,
                    is_follow_up: isFollowUp,
                    session_id: sessionId
                })
            });

            if (!response.ok) {
                throw new Error('Failed to get answer');
            }

            const data = await response.json();

            // Store session ID for follow-ups
            sessionId = data.session_id;
            lastQuestion = question;

            // Remove loading and show answer
            hideLoading();
            appendAnswer(data.answer, data.can_follow_up);

        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            appendAnswer("Oops! Something went wrong. Can you ask me again? 🦉", false);
        }
    }

    // Append question bubble to UI
    function appendQuestion(question) {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-bubble';
        questionDiv.innerHTML = `
            <div class="question-content">${escapeHtml(question)}</div>
            <span class="question-icon">👦</span>
        `;
        whyMessages.appendChild(questionDiv);
        scrollToBottom();
    }

    // Append answer bubble to UI
    function appendAnswer(answer, canFollowUp) {
        const answerDiv = document.createElement('div');
        answerDiv.className = 'answer-bubble';

        let actionsHtml = '';
        if (canFollowUp) {
            actionsHtml = `
                <div class="answer-actions">
                    <button class="btn-listen" onclick="speakText(this)">
                        <span>🔊</span> Listen
                    </button>
                    <button class="btn-more" onclick="askMore()">
                        <span>🤔</span> Tell Me More
                    </button>
                </div>
            `;
        }

        answerDiv.innerHTML = `
            <span class="answer-owl">🦉</span>
            <div class="answer-content">
                <div class="answer-text">${formatAnswer(answer)}</div>
                ${actionsHtml}
            </div>
        `;
        whyMessages.appendChild(answerDiv);
        scrollToBottom();
    }

    // Show loading indicator
    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-bubble';
        loadingDiv.id = 'loading-indicator';
        loadingDiv.innerHTML = `
            <span class="answer-owl">🦉</span>
            <div class="loading-content">
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        whyMessages.appendChild(loadingDiv);
        scrollToBottom();
    }

    // Hide loading indicator
    function hideLoading() {
        const loading = document.getElementById('loading-indicator');
        if (loading) {
            loading.remove();
        }
    }

    // Scroll to bottom of messages
    function scrollToBottom() {
        whyMessages.scrollTop = whyMessages.scrollHeight;
    }

    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Format answer text (handle line breaks, emojis)
    function formatAnswer(text) {
        return escapeHtml(text)
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    // Make askMore available globally
    window.askMore = async function() {
        if (!lastQuestion) return;

        // Add a "tell me more" indicator
        const moreDiv = document.createElement('div');
        moreDiv.className = 'question-bubble';
        moreDiv.innerHTML = `
            <div class="question-content">Tell me more! 🤔</div>
            <span class="question-icon">👦</span>
        `;
        whyMessages.appendChild(moreDiv);
        scrollToBottom();

        // Show loading
        showLoading();

        // Ask follow-up
        await askQuestion(lastQuestion, true);
    };

    // Make speakText available globally (Text-to-Speech)
    window.speakText = function(button) {
        const answerText = button.closest('.answer-content').querySelector('.answer-text').textContent;

        // Check if browser supports speech synthesis
        if ('speechSynthesis' in window) {
            // Cancel any ongoing speech
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(answerText);
            utterance.rate = 0.9; // Slightly slower for kids
            utterance.pitch = 1.1; // Slightly higher pitch

            // Try to find a friendly voice
            const voices = window.speechSynthesis.getVoices();
            const preferredVoice = voices.find(v =>
                v.name.includes('Samantha') ||
                v.name.includes('Karen') ||
                v.name.includes('Daniel') ||
                v.lang.startsWith('en')
            );
            if (preferredVoice) {
                utterance.voice = preferredVoice;
            }

            // Update button state
            button.innerHTML = '<span>🔊</span> Speaking...';
            button.disabled = true;

            utterance.onend = () => {
                button.innerHTML = '<span>🔊</span> Listen';
                button.disabled = false;
            };

            utterance.onerror = () => {
                button.innerHTML = '<span>🔊</span> Listen';
                button.disabled = false;
            };

            window.speechSynthesis.speak(utterance);
        } else {
            alert("Sorry, your browser doesn't support text-to-speech!");
        }
    };

    // Load voices (needed for some browsers)
    if ('speechSynthesis' in window) {
        window.speechSynthesis.getVoices();
    }
});

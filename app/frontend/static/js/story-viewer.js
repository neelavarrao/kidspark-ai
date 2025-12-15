/**
 * KidSpark AI Story Viewer
 *
 * Handles the display and interaction of stories in a modal interface
 */

document.addEventListener('DOMContentLoaded', () => {
    // Create and insert the modal structure into the page
    const storyModalHTML = `
        <div id="story-modal" class="story-modal">
            <div class="story-modal-content">
                <span class="story-modal-close">&times;</span>
                <div class="story-header">
                    <h1 class="story-title">Story Title</h1>
                    <div class="story-meta">
                        <span class="story-meta-item">
                            <i class="fas fa-clock"></i> <span class="story-duration">5 min</span>
                        </span>
                        <span class="story-meta-item">
                            <i class="fas fa-child"></i> <span class="story-age-range">3-5 years</span>
                        </span>
                        <span class="story-meta-item">
                            <i class="fas fa-map-marker-alt"></i> <span class="story-setting">Forest</span>
                        </span>
                    </div>
                    <button id="reading-mode-toggle" class="reading-mode-toggle">
                        Toggle Reading Mode
                    </button>
                </div>
                <div class="story-content">
                    Story content goes here...
                </div>
                <div class="story-footer">
                    <p class="story-moral">Moral: Be kind to others.</p>
                    <div class="story-discussion">
                        <h3>Discussion Questions</h3>
                        <ul id="discussion-questions">
                            <li>What did you think about the story?</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Insert the modal HTML into the page
    document.body.insertAdjacentHTML('beforeend', storyModalHTML);

    // Get references to modal elements
    const modal = document.getElementById('story-modal');
    const closeBtn = document.querySelector('.story-modal-close');
    const readingModeToggle = document.getElementById('reading-mode-toggle');

    // Add event listener for closing the modal
    closeBtn.addEventListener('click', () => {
        closeStoryModal();
    });

    // Close modal when clicking outside the content
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            closeStoryModal();
        }
    });

    // Toggle reading mode
    readingModeToggle.addEventListener('click', () => {
        document.body.classList.toggle('reading-mode');
    });

    // Close modal with escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeStoryModal();
        }
    });

    // Listen for messages that should trigger story display
    document.addEventListener('storyReceived', (event) => {
        const storyData = event.detail;
        if (storyData) {
            displayStory(storyData);
        }
    });
});

/**
 * Display a story in the modal
 * @param {Object} storyData - The story data to display
 */
function displayStory(storyData) {
    // Get references to modal elements
    const modal = document.getElementById('story-modal');
    const title = document.querySelector('.story-title');
    const duration = document.querySelector('.story-duration');
    const ageRange = document.querySelector('.story-age-range');
    const setting = document.querySelector('.story-setting');
    const content = document.querySelector('.story-content');
    const moral = document.querySelector('.story-moral');
    const questionsList = document.getElementById('discussion-questions');

    // Update the modal content with story data
    title.textContent = storyData.title || 'Untitled Story';
    duration.textContent = `${storyData.duration || 5} min`;
    ageRange.textContent = storyData.age_range || 'All ages';
    setting.textContent = storyData.setting || 'Various';

    // Format content with paragraphs
    content.innerHTML = formatStoryText(storyData.content);

    // Update moral
    moral.textContent = `Moral: ${storyData.moral || 'Be kind and thoughtful.'}`;

    // Update discussion questions
    questionsList.innerHTML = '';
    if (storyData.discussion && Array.isArray(storyData.discussion)) {
        storyData.discussion.forEach(question => {
            const li = document.createElement('li');
            li.textContent = question;
            questionsList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.textContent = 'What did you think about the story?';
        questionsList.appendChild(li);
    }

    // Show the modal
    openStoryModal();
}

/**
 * Format story text with proper paragraphs
 * @param {string} text - The raw story text
 * @returns {string} - HTML formatted text
 */
function formatStoryText(text) {
    if (!text) return '<p>Story content not available.</p>';

    // Split by double newlines for paragraphs
    const paragraphs = text.split(/\n\n|\r\n\r\n/);

    // Create HTML paragraphs
    return paragraphs.map(p => {
        // Skip empty paragraphs
        if (!p.trim()) return '';
        return `<p>${p}</p>`;
    }).join('');
}

/**
 * Open the story modal
 */
function openStoryModal() {
    const modal = document.getElementById('story-modal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Prevent scrolling behind modal
}

/**
 * Close the story modal
 */
function closeStoryModal() {
    const modal = document.getElementById('story-modal');
    modal.classList.remove('active');
    document.body.style.overflow = ''; // Restore scrolling
    document.body.classList.remove('reading-mode'); // Exit reading mode
}
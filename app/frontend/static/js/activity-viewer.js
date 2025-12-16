/**
 * KidSpark AI Activity Viewer
 *
 * Handles the display and interaction of activities in a modal interface
 */

document.addEventListener('DOMContentLoaded', () => {
    // Create and insert the modal structure into the page
    const activityModalHTML = `
        <div id="activity-modal" class="activity-modal">
            <div class="activity-modal-content">
                <span class="activity-modal-close">&times;</span>
                <div class="activity-header">
                    <h1 class="activity-title">Activity Title</h1>
                    <span class="activity-category-badge">Category</span>
                    <div class="activity-meta">
                        <span class="activity-meta-item">
                            <i class="fas fa-clock"></i> <span class="activity-duration">10 min</span>
                        </span>
                        <span class="activity-meta-item">
                            <i class="fas fa-hourglass-start"></i> <span class="activity-prep-time">5 min prep</span>
                        </span>
                        <span class="activity-meta-item">
                            <i class="fas fa-child"></i> <span class="activity-age-range">2-4 years</span>
                        </span>
                    </div>
                </div>
                <div class="activity-section">
                    <h3><i class="fas fa-list-ul"></i> What You'll Need</h3>
                    <ul id="activity-materials" class="activity-materials">
                        <li>Item 1</li>
                    </ul>
                </div>
                <div class="activity-section">
                    <h3><i class="fas fa-info-circle"></i> About This Activity</h3>
                    <p class="activity-description">Activity description goes here...</p>
                </div>
                <div class="activity-section activity-instructions-section">
                    <h3><i class="fas fa-hands-helping"></i> Parent Instructions</h3>
                    <p class="activity-instructions">Instructions go here...</p>
                </div>
                <div class="activity-section">
                    <h3><i class="fas fa-lightbulb"></i> Variations to Try</h3>
                    <ul id="activity-variations" class="activity-variations">
                        <li>Variation 1</li>
                    </ul>
                </div>
            </div>
        </div>
    `;

    // Insert the modal HTML into the page
    document.body.insertAdjacentHTML('beforeend', activityModalHTML);

    // Get references to modal elements
    const modal = document.getElementById('activity-modal');
    const closeBtn = document.querySelector('.activity-modal-close');

    // Add event listener for closing the modal
    closeBtn.addEventListener('click', () => {
        closeActivityModal();
    });

    // Close modal when clicking outside the content
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            closeActivityModal();
        }
    });

    // Close modal with escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeActivityModal();
        }
    });

    // Listen for messages that should trigger activity display
    document.addEventListener('activityReceived', (event) => {
        const activityData = event.detail;
        if (activityData) {
            displayActivity(activityData);
        }
    });
});

/**
 * Display an activity in the modal
 * @param {Object} activityData - The activity data to display
 */
function displayActivity(activityData) {
    // Get references to modal elements
    const modal = document.getElementById('activity-modal');
    const title = document.querySelector('.activity-title');
    const categoryBadge = document.querySelector('.activity-category-badge');
    const duration = document.querySelector('.activity-duration');
    const prepTime = document.querySelector('.activity-prep-time');
    const ageRange = document.querySelector('.activity-age-range');
    const materialsList = document.getElementById('activity-materials');
    const description = document.querySelector('.activity-description');
    const instructions = document.querySelector('.activity-instructions');
    const variationsList = document.getElementById('activity-variations');

    // Update the modal content with activity data
    title.textContent = activityData.name || 'Untitled Activity';
    categoryBadge.textContent = activityData.category || 'Activity';
    duration.textContent = `${activityData.duration || 10} min`;
    prepTime.textContent = `${activityData.prep_time || 5} min prep`;
    ageRange.textContent = activityData.age_range || 'All ages';

    // Update description
    description.textContent = activityData.description || 'No description available.';

    // Update instructions
    instructions.textContent = activityData.instructions || 'No instructions available.';

    // Update materials list
    materialsList.innerHTML = '';
    if (activityData.materials && Array.isArray(activityData.materials)) {
        activityData.materials.forEach(material => {
            const li = document.createElement('li');
            li.textContent = material;
            materialsList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.textContent = 'No specific materials needed';
        materialsList.appendChild(li);
    }

    // Update variations list
    variationsList.innerHTML = '';
    if (activityData.variations && Array.isArray(activityData.variations)) {
        activityData.variations.forEach(variation => {
            const li = document.createElement('li');
            li.textContent = variation;
            variationsList.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.textContent = 'Try different variations based on your child\'s interests!';
        variationsList.appendChild(li);
    }

    // Show the modal
    openActivityModal();
}

/**
 * Open the activity modal
 */
function openActivityModal() {
    const modal = document.getElementById('activity-modal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Prevent scrolling behind modal
}

/**
 * Close the activity modal
 */
function closeActivityModal() {
    const modal = document.getElementById('activity-modal');
    modal.classList.remove('active');
    document.body.style.overflow = ''; // Restore scrolling
}

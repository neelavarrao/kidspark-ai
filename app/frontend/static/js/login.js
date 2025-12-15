document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const errorMessage = document.getElementById('error-message');

    // Check if already logged in
    const token = localStorage.getItem('token');
    if (token) {
        window.location.href = '/chat';
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        errorMessage.style.display = 'none';

        try {
            const formData = new URLSearchParams();
            formData.append('username', email); // FastAPI OAuth2 expects 'username' not 'email'
            formData.append('password', password);

            const response = await fetch('/api/token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to login. Please check your email and password.');
            }

            const data = await response.json();

            // Store token
            localStorage.setItem('token', data.access_token);

            // Fetch user info
            const userResponse = await fetch('/api/users/me', {
                headers: {
                    'Authorization': `Bearer ${data.access_token}`
                }
            });

            if (!userResponse.ok) {
                throw new Error('Failed to get user information');
            }

            const userData = await userResponse.json();
            localStorage.setItem('user', JSON.stringify(userData));

            // Redirect to chat page
            window.location.href = '/chat';

        } catch (error) {
            errorMessage.textContent = error.message;
            errorMessage.style.display = 'block';
        }
    });
});
document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('register-form');
    const errorMessage = document.getElementById('error-message');

    // Check if already logged in
    const token = localStorage.getItem('token');
    if (token) {
        window.location.href = '/chat';
    }

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const name = document.getElementById('name').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm-password').value;

        // Reset error message
        errorMessage.style.display = 'none';

        // Validate passwords match
        if (password !== confirmPassword) {
            errorMessage.textContent = 'Passwords do not match';
            errorMessage.style.display = 'block';
            return;
        }

        // Validate password length
        if (password.length < 8) {
            errorMessage.textContent = 'Password must be at least 8 characters long';
            errorMessage.style.display = 'block';
            return;
        }

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name, email, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Registration failed. Please try again.');
            }

            // Registration successful, now login
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);

            const loginResponse = await fetch('/api/token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData
            });

            if (!loginResponse.ok) {
                throw new Error('Registration successful but login failed. Please login manually.');
            }

            const loginData = await loginResponse.json();

            // Store token
            localStorage.setItem('token', loginData.access_token);

            // Fetch user info
            const userResponse = await fetch('/api/users/me', {
                headers: {
                    'Authorization': `Bearer ${loginData.access_token}`
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
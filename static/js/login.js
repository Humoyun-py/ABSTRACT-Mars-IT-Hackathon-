// ==================== LOGIN PAGE ====================

const loginForm = document.getElementById('loginForm');
const errorMessage = document.getElementById('errorMessage');
const loginBtn = document.getElementById('loginBtn');

/**
 * Toggle password visibility
 */
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;
}

/**
 * Handle login form submission
 */
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Clear previous errors
    errorMessage.textContent = '';

    // Get form data
    const formData = new FormData(loginForm);
    const data = {
        email: formData.get('email'),
        password: formData.get('password')
    };

    // Show loading state
    loginBtn.classList.add('loading');
    loginBtn.disabled = true;

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            // Success - redirect
            window.location.href = result.redirect;
        } else {
            // Show error
            errorMessage.textContent = result.error || 'Xatolik yuz berdi';
            loginBtn.classList.remove('loading');
            loginBtn.disabled = false;
        }
    } catch (error) {
        errorMessage.textContent = 'Server bilan bog\'lanishda xatolik: ' + error.message;
        loginBtn.classList.remove('loading');
        loginBtn.disabled = false;
    }
});

// Auto-focus email input
document.getElementById('email').focus();

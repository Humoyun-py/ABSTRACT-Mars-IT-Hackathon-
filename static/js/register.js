// ==================== REGISTER PAGE ====================

const registerForm = document.getElementById('registerForm');
const errorMessage = document.getElementById('errorMessage');
const registerBtn = document.getElementById('registerBtn');

/**
 * Toggle password visibility
 */
function togglePassword(fieldId) {
    const passwordInput = document.getElementById(fieldId);
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;
}

/**
 * Validate password match
 */
function validatePasswords() {
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;

    if (password !== confirmPassword) {
        errorMessage.textContent = '❌ Parollar mos kelmaydi!';
        return false;
    }

    if (password.length < 6) {
        errorMessage.textContent = '❌ Parol kamida 6 ta belgidan iborat bo\'lishi kerak!';
        return false;
    }

    return true;
}

/**
 * Handle register form submission
 */
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Clear previous errors
    errorMessage.textContent = '';

    // Validate passwords
    if (!validatePasswords()) {
        return;
    }

    // Get form data
    const formData = new FormData(registerForm);
    const data = {
        full_name: formData.get('full_name'),
        email: formData.get('email'),
        phone: formData.get('phone'),
        position: formData.get('position'),
        department: formData.get('department'),
        password: formData.get('password')
    };

    // Show loading state
    registerBtn.classList.add('loading');
    registerBtn.disabled = true;

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            // Success - show message and redirect to login
            alert('✅ Ro\'yxatdan o\'tdingiz! Endi tizimga kirishingiz mumkin.');
            window.location.href = '/login';
        } else {
            // Show error
            errorMessage.textContent = result.error || 'Xatolik yuz berdi';
            registerBtn.classList.remove('loading');
            registerBtn.disabled = false;
        }
    } catch (error) {
        errorMessage.textContent = 'Server bilan bog\'lanishda xatolik: ' + error.message;
        registerBtn.classList.remove('loading');
        registerBtn.disabled = false;
    }
});

// Real-time password match validation
document.getElementById('confirm_password').addEventListener('input', () => {
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;

    if (confirmPassword && password !== confirmPassword) {
        errorMessage.textContent = '⚠️ Parollar mos kelmaydi';
    } else {
        errorMessage.textContent = '';
    }
});

// Auto-focus full name input
document.getElementById('full_name').focus();

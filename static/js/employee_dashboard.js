// ==================== EMPLOYEE DASHBOARD ====================

/**
 * Load employee data
 */
async function loadEmployeeData() {
    try {
        const response = await fetch('/api/me');
        const data = await response.json();
        console.log('Employee data:', data);
    } catch (error) {
        console.error('Error loading employee data:', error);
    }
}

/**
 * Handle task checkbox changes
 */
document.querySelectorAll('.task-item input[type="checkbox"]').forEach(checkbox => {
    checkbox.addEventListener('change', async (e) => {
        const taskItem = e.target.closest('.task-item');

        if (e.target.checked) {
            taskItem.style.opacity = '0.5';
            showNotification('Vazifa bajarildi! ✅', 'success');
        } else {
            taskItem.style.opacity = '1';
        }
    });
});

// Load data on page load
document.addEventListener('DOMContentLoaded', () => {
    loadEmployeeData();
});

// ==================== ADMIN PANEL ====================

/**
 * Set active menu item based on current URL
 */
function setActiveMenuItem() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
        }
    });
}

// Run on page load
document.addEventListener('DOMContentLoaded', () => {
    setActiveMenuItem();
});

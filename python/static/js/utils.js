/**
 * Utility functions for the application
 */

function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Trigger a reflow to enable the transition
    toast.offsetHeight;
    
    // Show the toast
    toast.classList.add('show');
    
    // Remove the toast after duration
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300); // matches transition duration
    }, duration);
}


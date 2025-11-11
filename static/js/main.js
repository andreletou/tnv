// Main JavaScript file for Marketplace App

// Global variables
let cartCount = 0;
let isLoading = false;

// DOM ready
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Initialize cart count
    updateCartCount();
    
    // Initialize pull to refresh
    initializePullToRefresh();
    
    // Initialize search functionality
    initializeSearch();
    
    // Initialize mobile navigation
    initializeMobileNav();
    
    // Initialize lazy loading
    initializeLazyLoading();
    
    // Initialize touch gestures
    initializeTouchGestures();
    
    // Initialize offline detection
    initializeOfflineDetection();
}

// Cart management
function updateCartCount() {
    fetch('/clients/api/panier/infos/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            cartCount = data.nombre_articles;
            const cartCountElement = document.getElementById('cart-count');
            if (cartCountElement) {
                cartCountElement.textContent = cartCount;
                if (cartCount > 0) {
                    cartCountElement.classList.add('badge-pulse');
                } else {
                    cartCountElement.classList.remove('badge-pulse');
                }
            }
        }
    })
    .catch(error => console.error('Error updating cart count:', error));
}

// Pull to refresh
function initializePullToRefresh() {
    let startY = 0;
    let isPulling = false;
    const pullThreshold = 80;
    
    const body = document.body;
    const pullIndicator = document.createElement('div');
    pullIndicator.className = 'fixed top-0 left-0 right-0 h-20 bg-primary-500 flex items-center justify-center text-white z-50 transform -translate-y-full transition-transform duration-300';
    pullIndicator.innerHTML = '<i class="fas fa-arrow-down mr-2"></i>Tirer pour rafraîchir';
    body.appendChild(pullIndicator);
    
    body.addEventListener('touchstart', (e) => {
        if (window.scrollY === 0) {
            startY = e.touches[0].clientY;
            isPulling = true;
        }
    });
    
    body.addEventListener('touchmove', (e) => {
        if (!isPulling) return;
        
        const currentY = e.touches[0].clientY;
        const pullDistance = currentY - startY;
        
        if (pullDistance > 0 && pullDistance < pullThreshold * 2) {
            pullIndicator.style.transform = `translateY(${Math.min(pullDistance - pullThreshold, 0)}px)`;
            
            if (pullDistance > pullThreshold) {
                pullIndicator.innerHTML = '<i class="fas fa-arrow-up mr-2"></i>Relâcher pour rafraîchir';
                pullIndicator.classList.add('bg-primary-600');
            } else {
                pullIndicator.innerHTML = '<i class="fas fa-arrow-down mr-2"></i>Tirer pour rafraîchir';
                pullIndicator.classList.remove('bg-primary-600');
            }
        }
    });
    
    body.addEventListener('touchend', () => {
        if (!isPulling) return;
        isPulling = false;
        
        const pullDistance = parseInt(pullIndicator.style.transform.match(/-?\d+/)?.[0] || 0);
        
        if (pullDistance >= 0) {
            // Refresh the page
            location.reload();
        } else {
            pullIndicator.style.transform = 'translateY(-100%)';
        }
    });
}

// Search functionality
function initializeSearch() {
    const searchInputs = document.querySelectorAll('[data-search]');
    
    searchInputs.forEach(input => {
        let searchTimeout;
        
        input.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            if (query.length >= 2) {
                searchTimeout = setTimeout(() => {
                    performSearch(query);
                }, 300);
            }
        });
    });
}

function performSearch(query) {
    const searchUrl = `/clients/recherche/?q=${encodeURIComponent(query)}`;
    
    // Show loading state
    showLoading();
    
    // Navigate to search results
    window.location.href = searchUrl;
}

// Mobile navigation
function initializeMobileNav() {
    const navItems = document.querySelectorAll('.bottom-nav a');
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            // Add ripple effect
            const ripple = document.createElement('span');
            ripple.className = 'absolute inset-0 bg-primary-500 opacity-20 rounded-lg animate-ping';
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });
}

// Lazy loading for images
function initializeLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy-image');
                img.classList.add('loaded');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => {
        img.classList.add('lazy-image');
        imageObserver.observe(img);
    });
}

// Touch gestures
function initializeTouchGestures() {
    const swipeableElements = document.querySelectorAll('[data-swipeable]');
    
    swipeableElements.forEach(element => {
        let startX = 0;
        let startY = 0;
        
        element.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });
        
        element.addEventListener('touchend', (e) => {
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            
            const deltaX = endX - startX;
            const deltaY = endY - startY;
            
            // Check if it's a horizontal swipe
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                if (deltaX > 0) {
                    // Swipe right
                    element.dispatchEvent(new CustomEvent('swiperight'));
                } else {
                    // Swipe left
                    element.dispatchEvent(new CustomEvent('swipeleft'));
                }
            }
        });
    });
}

// Offline detection
function initializeOfflineDetection() {
    const offlineIndicator = document.createElement('div');
    offlineIndicator.className = 'fixed top-0 left-0 right-0 bg-red-500 text-white text-center py-2 z-50 hidden';
    offlineIndicator.innerHTML = '<i class="fas fa-wifi-slash mr-2"></i>Vous êtes hors ligne';
    document.body.appendChild(offlineIndicator);
    
    window.addEventListener('online', () => {
        offlineIndicator.classList.add('hidden');
        showNotification('Connexion rétablie', 'success');
    });
    
    window.addEventListener('offline', () => {
        offlineIndicator.classList.remove('hidden');
        showNotification('Vous êtes hors ligne', 'error');
    });
}

// Loading states
function showLoading() {
    isLoading = true;
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('hidden');
    }
}

function hideLoading() {
    isLoading = false;
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

// Notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 max-w-sm animate-slide-up rounded-lg shadow-lg p-4 ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        type === 'warning' ? 'bg-yellow-500 text-white' :
        'bg-blue-500 text-white'
    }`;
    
    notification.innerHTML = `
        <div class="flex items-center justify-between">
            <p class="text-sm font-medium">${message}</p>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white hover:text-gray-200">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Modal management
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }
}

// Close modals on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
        const modal = e.target.closest('.modal');
        if (modal) {
            closeModal(modal.id);
        }
    }
});

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('border-red-500');
            
            // Remove error class on input
            input.addEventListener('input', () => {
                if (input.value.trim()) {
                    input.classList.remove('border-red-500');
                }
            });
        }
    });
    
    return isValid;
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'XOF',
        minimumFractionDigits: 0
    }).format(amount);
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Copy to clipboard
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copié dans le presse-papiers', 'success');
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showNotification('Copié dans le presse-papiers', 'success');
    }
}

// Share functionality
async function shareContent(title, text, url) {
    if (navigator.share) {
        try {
            await navigator.share({
                title: title,
                text: text,
                url: url
            });
        } catch (error) {
            console.log('Error sharing:', error);
        }
    } else {
        // Fallback: copy to clipboard
        copyToClipboard(url);
    }
}

// Initialize service worker for PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('SW registered: ', registration);
            })
            .catch(registrationError => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// Export functions for global use
window.marketplace = {
    showLoading,
    hideLoading,
    showNotification,
    openModal,
    closeModal,
    validateForm,
    formatCurrency,
    formatDate,
    copyToClipboard,
    shareContent,
    updateCartCount
};
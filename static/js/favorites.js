// Favorites functionality for Local-Links

class Favorites {
    constructor() {
        this.favorites = [];
        this.init();
    }

    init() {
        this.loadFavoritesFromStorage();
        this.setupEventListeners();
        this.updateFavoritesUI();
    }

    loadFavoritesFromStorage() {
        const savedFavorites = localStorage.getItem('Local-links_favorites');
        if (savedFavorites) {
            try {
                this.favorites = JSON.parse(savedFavorites);
            } catch (error) {
                console.error('Error loading favorites from storage:', error);
                this.favorites = [];
            }
        }
    }

    saveFavoritesToStorage() {
        localStorage.setItem('Local-links_favorites', JSON.stringify(this.favorites));
    }

    setupEventListeners() {
        // Listen for favorites updates from other tabs
        window.addEventListener('storage', (e) => {
            if (e.key === 'Local-links_favorites') {
                this.loadFavoritesFromStorage();
                this.updateFavoritesUI();
            }
        });

        // Listen for custom favorites events
        document.addEventListener('favorites:updated', () => {
            this.updateFavoritesUI();
        });
    }

    async addToFavorites(productId) {
        try {
            showLoading();
            
            // Call API to add to favorites
            const response = await window.API.safe.favorites.add(productId);
            
            if (response.success) {
                // Update local favorites
                if (!this.favorites.includes(productId)) {
                    this.favorites.push(productId);
                    this.saveFavoritesToStorage();
                    this.updateFavoritesUI();
                }
                
                showToast(response.message || 'Produit ajouté aux favoris', 'success');
                
                // Trigger custom event
                this.dispatchFavoritesEvent('item:added', { productId });
                
                // Update heart icon
                this.updateHeartIcon(productId, true);
                
                return response;
            } else {
                showToast(response.message || 'Erreur lors de l\'ajout aux favoris', 'error');
                return null;
            }
        } catch (error) {
            console.error('Error adding to favorites:', error);
            showToast('Erreur lors de l\'ajout aux favoris', 'error');
            return null;
        } finally {
            hideLoading();
        }
    }

    async removeFromFavorites(productId) {
        try {
            showLoading();
            
            // Call API to remove from favorites
            const response = await window.API.safe.favorites.remove(productId);
            
            if (response.success) {
                // Update local favorites
                this.favorites = this.favorites.filter(id => id !== productId);
                this.saveFavoritesToStorage();
                this.updateFavoritesUI();
                
                showToast(response.message || 'Produit retiré des favoris', 'success');
                
                // Trigger custom event
                this.dispatchFavoritesEvent('item:removed', { productId });
                
                // Update heart icon
                this.updateHeartIcon(productId, false);
                
                return response;
            } else {
                showToast(response.message || 'Erreur lors du retrait des favoris', 'error');
                return null;
            }
        } catch (error) {
            console.error('Error removing from favorites:', error);
            showToast('Erreur lors du retrait des favoris', 'error');
            return null;
        } finally {
            hideLoading();
        }
    }

    async toggleFavorite(productId) {
        if (this.isFavorite(productId)) {
            return this.removeFromFavorites(productId);
        } else {
            return this.addToFavorites(productId);
        }
    }

    updateFavoritesUI() {
        // Update all heart icons on the page
        this.updateAllHeartIcons();
        
        // Update favorites count if on favorites page
        this.updateFavoritesCount();
    }

    updateAllHeartIcons() {
        const heartButtons = document.querySelectorAll('[onclick*="toggleFavorite"], [data-favorite-product-id]');
        
        heartButtons.forEach(button => {
            const productId = this.extractProductId(button);
            if (productId) {
                this.updateHeartIcon(productId, this.isFavorite(productId), button);
            }
        });
    }

    updateHeartIcon(productId, isFavorite, button = null) {
        if (!button) {
            button = document.querySelector(`[onclick*="toggleFavorite(${productId})"], [data-favorite-product-id="${productId}"]`);
        }
        
        if (!button) return;
        
        const icon = button.querySelector('i') || button;
        const isHeartIcon = icon.classList.contains('fa-heart') || icon.classList.contains('fa-heart');
        
        if (isHeartIcon) {
            if (isFavorite) {
                icon.classList.remove('far');
                icon.classList.add('fas', 'text-red-500');
            } else {
                icon.classList.remove('fas', 'text-red-500');
                icon.classList.add('far');
            }
        }
        
        // Update button title
        button.title = isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris';
        
        // Add animation
        icon.classList.add('animate-pulse');
        setTimeout(() => {
            icon.classList.remove('animate-pulse');
        }, 500);
    }

    updateFavoritesCount() {
        const countElements = document.querySelectorAll('#favorites-count, .favorites-count');
        countElements.forEach(element => {
            element.textContent = this.favorites.length;
        });
    }

    extractProductId(element) {
        // Extract product ID from onclick attribute
        const onclick = element.getAttribute('onclick');
        if (onclick) {
            const match = onclick.match(/toggleFavorite\((\d+)\)/);
            if (match) return parseInt(match[1]);
        }
        
        // Extract from data attribute
        const dataId = element.getAttribute('data-favorite-product-id');
        if (dataId) return parseInt(dataId);
        
        return null;
    }

    async syncFavoritesWithServer() {
        try {
            const response = await window.API.safe.favorites.get();
            if (response.success && response.favorites) {
                // Update local favorites with server data
                this.favorites = response.favorites.map(fav => fav.produit.id);
                this.saveFavoritesToStorage();
                this.updateFavoritesUI();
            }
        } catch (error) {
            console.error('Error syncing favorites with server:', error);
        }
    }

    clearFavorites() {
        this.favorites = [];
        this.saveFavoritesToStorage();
        this.updateFavoritesUI();
    }

    dispatchFavoritesEvent(eventType, data = {}) {
        const event = new CustomEvent(`favorites:${eventType}`, {
            detail: {
                favorites: [...this.favorites],
                count: this.favorites.length,
                ...data
            }
        });
        document.dispatchEvent(event);
    }

    // Utility methods
    getFavorites() {
        return [...this.favorites];
    }

    getCount() {
        return this.favorites.length;
    }

    isFavorite(productId) {
        return this.favorites.includes(productId);
    }

    isEmpty() {
        return this.favorites.length === 0;
    }
}

// Initialize favorites
const favorites = new Favorites();

// Global functions for backward compatibility
function toggleFavorite(productId) {
    return favorites.toggleFavorite(productId);
}

function addToFavorites(productId) {
    return favorites.addToFavorites(productId);
}

function removeFromFavorites(productId) {
    return favorites.removeFromFavorites(productId);
}

function toggleBoutiqueFavorite(boutiqueId) {
    // For boutique favorites (different implementation)
    console.log('Toggle boutique favorite:', boutiqueId);
    // Implementation would be similar but for boutiques
}

// Auto-sync favorites when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Sync with server if user is authenticated
    if (document.body.classList.contains('user-authenticated')) {
        favorites.syncFavoritesWithServer();
    }
});

// Export for global use
window.Favorites = favorites;
window.favorites = favorites;
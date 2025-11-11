// API JavaScript file for Marketplace App

// API base configuration
const API_BASE = '';
const API_HEADERS = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest'
};

// Cart API
class CartAPI {
    static async addItem(productId, quantity = 1) {
        try {
            const response = await fetch(`${API_BASE}/clients/api/panier/ajouter/`, {
                method: 'POST',
                headers: API_HEADERS,
                body: JSON.stringify({
                    produit_id: productId,
                    quantite: quantity
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                marketplace.updateCartCount();
                marketplace.showNotification(data.message, 'success');
                return data;
            } else {
                marketplace.showNotification(data.message, 'error');
                return null;
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            marketplace.showNotification('Erreur lors de l\'ajout au panier', 'error');
            return null;
        }
    }
    
    static async updateItem(itemId, quantity) {
        try {
            const response = await fetch(`${API_BASE}/clients/api/panier/modifier/`, {
                method: 'POST',
                headers: API_HEADERS,
                body: JSON.stringify({
                    item_id: itemId,
                    quantite: quantity
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                marketplace.updateCartCount();
                marketplace.showNotification(data.message, 'success');
                return data;
            } else {
                marketplace.showNotification(data.message, 'error');
                return null;
            }
        } catch (error) {
            console.error('Error updating cart:', error);
            marketplace.showNotification('Erreur lors de la mise à jour du panier', 'error');
            return null;
        }
    }
    
    static async removeItem(itemId) {
        try {
            const response = await fetch(`${API_BASE}/clients/api/panier/supprimer/`, {
                method: 'POST',
                headers: API_HEADERS,
                body: JSON.stringify({
                    item_id: itemId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                marketplace.updateCartCount();
                marketplace.showNotification(data.message, 'success');
                return data;
            } else {
                marketplace.showNotification(data.message, 'error');
                return null;
            }
        } catch (error) {
            console.error('Error removing from cart:', error);
            marketplace.showNotification('Erreur lors de la suppression du panier', 'error');
            return null;
        }
    }
    
    static async getCartInfo() {
        try {
            const response = await fetch(`${API_BASE}/clients/api/panier/infos/`, {
                method: 'GET',
                headers: API_HEADERS
            });
            
            const data = await response.json();
            return data.success ? data : null;
        } catch (error) {
            console.error('Error getting cart info:', error);
            return null;
        }
    }
}

// Favorites API
class FavoritesAPI {
    static async add(productId) {
        try {
            const response = await fetch(`${API_BASE}/clients/api/favoris/ajouter/`, {
                method: 'POST',
                headers: API_HEADERS,
                body: JSON.stringify({
                    produit_id: productId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                marketplace.showNotification(data.message, 'success');
                return data;
            } else {
                marketplace.showNotification(data.message, 'error');
                return null;
            }
        } catch (error) {
            console.error('Error adding to favorites:', error);
            marketplace.showNotification('Erreur lors de l\'ajout aux favoris', 'error');
            return null;
        }
    }
    
    static async remove(productId) {
        try {
            const response = await fetch(`${API_BASE}/clients/api/favoris/supprimer/`, {
                method: 'POST',
                headers: API_HEADERS,
                body: JSON.stringify({
                    produit_id: productId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                marketplace.showNotification(data.message, 'success');
                return data;
            } else {
                marketplace.showNotification(data.message, 'error');
                return null;
            }
        } catch (error) {
            console.error('Error removing from favorites:', error);
            marketplace.showNotification('Erreur lors de la suppression des favoris', 'error');
            return null;
        }
    }
}

// Reviews API
class ReviewsAPI {
    static async add(productId, note, commentaire) {
        try {
            const response = await fetch(`${API_BASE}/clients/api/avis/ajouter/`, {
                method: 'POST',
                headers: API_HEADERS,
                body: JSON.stringify({
                    produit_id: productId,
                    note: note,
                    commentaire: commentaire
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                marketplace.showNotification(data.message, 'success');
                return data;
            } else {
                marketplace.showNotification(data.message, 'error');
                return null;
            }
        } catch (error) {
            console.error('Error adding review:', error);
            marketplace.showNotification('Erreur lors de l\'ajout de l\'avis', 'error');
            return null;
        }
    }
}

// Products API
class ProductsAPI {
    static async getSuggestions(productId = null, limit = 4) {
        try {
            const url = productId 
                ? `${API_BASE}/clients/api/produits/suggestions/?produit_id=${productId}&limit=${limit}`
                : `${API_BASE}/clients/api/produits/suggestions/?limit=${limit}`;
                
            const response = await fetch(url, {
                method: 'GET',
                headers: API_HEADERS
            });
            
            const data = await response.json();
            return data.success ? data.suggestions : [];
        } catch (error) {
            console.error('Error getting suggestions:', error);
            return [];
        }
    }
}

// Orders API
class OrdersAPI {
    static async updateStatus(orderId, status) {
        try {
            const response = await fetch(`${API_BASE}/clients/api/commande/statut/`, {
                method: 'POST',
                headers: API_HEADERS,
                body: JSON.stringify({
                    commande_id: orderId,
                    statut: status
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                marketplace.showNotification(data.message, 'success');
                return data;
            } else {
                marketplace.showNotification(data.message, 'error');
                return null;
            }
        } catch (error) {
            console.error('Error updating order status:', error);
            marketplace.showNotification('Erreur lors de la mise à jour du statut', 'error');
            return null;
        }
    }
}

// Merchant API
class MerchantAPI {
    static async getStatistics() {
        try {
            const response = await fetch(`${API_BASE}/commercants/api/statistiques/`, {
                method: 'GET',
                headers: API_HEADERS
            });
            
            const data = await response.json();
            return data.success ? data.statistiques : null;
        } catch (error) {
            console.error('Error getting statistics:', error);
            return null;
        }
    }
    
    static async getOrders(status = '', page = 1) {
        try {
            const url = status 
                ? `${API_BASE}/commercants/api/commandes/?statut=${status}&page=${page}`
                : `${API_BASE}/commercants/api/commandes/?page=${page}`;
                
            const response = await fetch(url, {
                method: 'GET',
                headers: API_HEADERS
            });
            
            const data = await response.json();
            return data.success ? data : null;
        } catch (error) {
            console.error('Error getting orders:', error);
            return null;
        }
    }
    
    static async getOrderDetails(orderId) {
        try {
            const response = await fetch(`${API_BASE}/commercants/api/commande/${orderId}/`, {
                method: 'GET',
                headers: API_HEADERS
            });
            
            const data = await response.json();
            return data.success ? data.commande : null;
        } catch (error) {
            console.error('Error getting order details:', error);
            return null;
        }
    }
    
    static async updateOrderStatus(orderId, status) {
        try {
            const response = await fetch(`${API_BASE}/commercants/api/commande/${orderId}/statut/`, {
                method: 'POST',
                headers: API_HEADERS,
                body: JSON.stringify({
                    statut: status
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                marketplace.showNotification(data.message, 'success');
                return data;
            } else {
                marketplace.showNotification(data.message, 'error');
                return null;
            }
        } catch (error) {
            console.error('Error updating order status:', error);
            marketplace.showNotification('Erreur lors de la mise à jour du statut', 'error');
            return null;
        }
    }
    
    static async getProductStats() {
        try {
            const response = await fetch(`${API_BASE}/commercants/api/produits/stats/`, {
                method: 'GET',
                headers: API_HEADERS
            });
            
            const data = await response.json();
            return data.success ? data : null;
        } catch (error) {
            console.error('Error getting product stats:', error);
            return null;
        }
    }
    
    static async getNotifications() {
        try {
            const response = await fetch(`${API_BASE}/commercants/api/notifications/`, {
                method: 'GET',
                headers: API_HEADERS
            });
            
            const data = await response.json();
            return data.success ? data.notifications : null;
        } catch (error) {
            console.error('Error getting notifications:', error);
            return null;
        }
    }
}

// Form handling
class FormHandler {
    static async submitForm(formId, url, method = 'POST') {
        const form = document.getElementById(formId);
        if (!form) return null;
        
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Handle file uploads
        const fileInputs = form.querySelectorAll('input[type="file"]');
        for (const input of fileInputs) {
            if (input.files.length > 0) {
                data[input.name] = input.files[0];
            }
        }
        
        marketplace.showLoading();
        
        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                marketplace.showNotification(result.message || 'Opération réussie', 'success');
                return result;
            } else {
                const errorMessage = result.errors ? Object.values(result.errors).flat().join(', ') : result.message;
                marketplace.showNotification(errorMessage || 'Erreur lors de l\'opération', 'error');
                return null;
            }
        } catch (error) {
            console.error('Error submitting form:', error);
            marketplace.showNotification('Erreur lors de la soumission du formulaire', 'error');
            return null;
        } finally {
            marketplace.hideLoading();
        }
    }
}

// Real-time updates
class RealTimeUpdates {
    static initialize() {
        // Check for updates every 30 seconds
        setInterval(() => {
            this.checkForUpdates();
        }, 30000);
    }
    
    static async checkForUpdates() {
        // Update cart count
        marketplace.updateCartCount();
        
        // Check for new notifications if merchant
        if (window.location.pathname.includes('/commercants/')) {
            const notifications = await MerchantAPI.getNotifications();
            if (notifications && notifications.total > 0) {
                this.updateNotificationBadge(notifications.total);
            }
        }
    }
    
    static updateNotificationBadge(count) {
        let badge = document.getElementById('notification-badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.id = 'notification-badge';
            badge.className = 'absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center badge-pulse';
            
            const ordersNav = document.querySelector('a[href*="commandes"]');
            if (ordersNav) {
                ordersNav.style.position = 'relative';
                ordersNav.appendChild(badge);
            }
        }
        
        badge.textContent = count;
        badge.style.display = count > 0 ? 'flex' : 'none';
    }
}

// Search suggestions
class SearchSuggestions {
    static async getSuggestions(query) {
        if (query.length < 2) return [];
        
        try {
            const response = await fetch(`${API_BASE}/clients/api/produits/suggestions/?search=${encodeURIComponent(query)}`, {
                method: 'GET',
                headers: API_HEADERS
            });
            
            const data = await response.json();
            return data.success ? data.suggestions : [];
        } catch (error) {
            console.error('Error getting search suggestions:', error);
            return [];
        }
    }
}

// Export API classes
window.API = {
    Cart: CartAPI,
    Favorites: FavoritesAPI,
    Reviews: ReviewsAPI,
    Products: ProductsAPI,
    Orders: OrdersAPI,
    Merchant: MerchantAPI,
    Form: FormHandler,
    RealTime: RealTimeUpdates,
    Search: SearchSuggestions
};

// Initialize real-time updates
document.addEventListener('DOMContentLoaded', () => {
    RealTimeUpdates.initialize();
});
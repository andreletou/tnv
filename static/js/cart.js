// Cart functionality for Marketplace Togo

class Cart {
    constructor() {
        this.items = [];
        this.total = 0;
        this.itemCount = 0;
        this.init();
    }

    init() {
        this.loadCartFromStorage();
        this.setupEventListeners();
        this.updateCartUI();
    }

    loadCartFromStorage() {
        const savedCart = localStorage.getItem('marketplace_cart');
        if (savedCart) {
            try {
                const cartData = JSON.parse(savedCart);
                this.items = cartData.items || [];
                this.total = cartData.total || 0;
                this.itemCount = cartData.itemCount || 0;
            } catch (error) {
                console.error('Error loading cart from storage:', error);
                this.clearCart();
            }
        }
    }

    saveCartToStorage() {
        const cartData = {
            items: this.items,
            total: this.total,
            itemCount: this.itemCount,
            timestamp: Date.now()
        };
        localStorage.setItem('marketplace_cart', JSON.stringify(cartData));
    }

    setupEventListeners() {
        // Listen for cart updates from other tabs
        window.addEventListener('storage', (e) => {
            if (e.key === 'marketplace_cart') {
                this.loadCartFromStorage();
                this.updateCartUI();
            }
        });

        // Listen for custom cart events
        document.addEventListener('cart:updated', () => {
            this.updateCartUI();
        });

        // Listen for page visibility changes to sync cart
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.syncCartWithServer();
            }
        });
    }

    async addToCart(productId, quantity = 1, options = {}) {
        try {
            showLoading();
            
            // Call API to add to cart
            const response = await window.API.safe.cart.add(productId, quantity);
            
            if (response.success) {
                // Update local cart
                const existingItem = this.items.find(item => item.productId === productId);
                
                if (existingItem) {
                    existingItem.quantity += quantity;
                    existingItem.subtotal = existingItem.price * existingItem.quantity;
                } else {
                    this.items.push({
                        productId: productId,
                        quantity: quantity,
                        price: response.article?.prix_unitaire || 0,
                        subtotal: response.article?.sous_total || 0,
                        name: response.article?.produit_nom || '',
                        image: response.article?.produit_image || ''
                    });
                }
                
                this.calculateTotals();
                this.saveCartToStorage();
                this.updateCartUI();
                
                // Show success message
                showToast(response.message || 'Produit ajouté au panier', 'success');
                
                // Trigger custom event
                this.dispatchCartEvent('item:added', {
                    productId,
                    quantity,
                    item: response.article
                });
                
                // Update cart count globally
                this.updateCartCount(response.nombre_articles || this.itemCount);
                
                return response;
            } else {
                showToast(response.message || 'Erreur lors de l\'ajout au panier', 'error');
                return null;
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            showToast('Erreur lors de l\'ajout au panier', 'error');
            return null;
        } finally {
            hideLoading();
        }
    }

    async updateQuantity(itemId, newQuantity) {
        if (newQuantity < 1) {
            return this.removeFromCart(itemId);
        }

        try {
            showLoading();
            
            const response = await window.API.safe.cart.update(itemId, newQuantity);
            
            if (response.success) {
                // Update local cart
                const item = this.items.find(item => item.productId === itemId);
                if (item) {
                    if (response.article) {
                        item.quantity = response.article.quantite;
                        item.subtotal = response.article.sous_total;
                    } else {
                        // Item was removed
                        this.items = this.items.filter(item => item.productId !== itemId);
                    }
                }
                
                this.calculateTotals();
                this.saveCartToStorage();
                this.updateCartUI();
                
                showToast(response.message || 'Quantité mise à jour', 'success');
                
                // Update cart count globally
                this.updateCartCount(response.nombre_articles || this.itemCount);
                
                return response;
            } else {
                showToast(response.message || 'Erreur lors de la mise à jour', 'error');
                return null;
            }
        } catch (error) {
            console.error('Error updating cart quantity:', error);
            showToast('Erreur lors de la mise à jour', 'error');
            return null;
        } finally {
            hideLoading();
        }
    }

    async removeFromCart(itemId) {
        if (!confirm('Êtes-vous sûr de vouloir supprimer cet article ?')) {
            return;
        }

        try {
            showLoading();
            
            const response = await window.API.safe.cart.remove(itemId);
            
            if (response.success) {
                // Update local cart
                this.items = this.items.filter(item => item.productId !== itemId);
                
                this.calculateTotals();
                this.saveCartToStorage();
                this.updateCartUI();
                
                showToast(response.message || 'Article supprimé du panier', 'success');
                
                // Trigger custom event
                this.dispatchCartEvent('item:removed', { itemId });
                
                // Update cart count globally
                this.updateCartCount(response.nombre_articles || this.itemCount);
                
                // Check if cart is empty
                if (this.items.length === 0) {
                    this.handleEmptyCart();
                }
                
                return response;
            } else {
                showToast(response.message || 'Erreur lors de la suppression', 'error');
                return null;
            }
        } catch (error) {
            console.error('Error removing from cart:', error);
            showToast('Erreur lors de la suppression', 'error');
            return null;
        } finally {
            hideLoading();
        }
    }

    calculateTotals() {
        this.total = this.items.reduce((sum, item) => sum + item.subtotal, 0);
        this.itemCount = this.items.reduce((sum, item) => sum + item.quantity, 0);
    }

    updateCartUI() {
        // Update cart count badges
        const cartCountElements = document.querySelectorAll('#cart-count, #mobile-cart-count');
        cartCountElements.forEach(element => {
            element.textContent = this.itemCount;
        });

        // Update cart total if on cart page
        const totalElements = document.querySelectorAll('#cart-total, #total-cost');
        totalElements.forEach(element => {
            element.textContent = window.Marketplace.formatPrice(this.total);
        });

        // Update cart items if on cart page
        this.updateCartItemsUI();
    }

    updateCartItemsUI() {
        const cartContainer = document.getElementById('cart-items-container');
        if (!cartContainer) return;

        if (this.items.length === 0) {
            cartContainer.innerHTML = `
                <div class="text-center py-8">
                    <i class="fas fa-shopping-cart text-gray-300 text-5xl mb-4"></i>
                    <p class="text-gray-600">Votre panier est vide</p>
                </div>
            `;
            return;
        }

        const itemsHTML = this.items.map(item => `
            <div class="cart-item border rounded-lg p-4 mb-4" data-product-id="${item.productId}">
                <div class="flex gap-4">
                    <img src="${item.image || '/static/images/placeholder.jpg'}" alt="${item.name}" class="w-20 h-20 object-cover rounded">
                    <div class="flex-1">
                        <h4 class="font-semibold">${item.name}</h4>
                        <p class="text-gray-600">${window.Marketplace.formatPrice(item.price)}</p>
                        <div class="flex items-center gap-2 mt-2">
                            <button onclick="cart.updateQuantity(${item.productId}, ${item.quantity - 1})" class="w-8 h-8 border rounded hover:bg-gray-100">
                                <i class="fas fa-minus text-xs"></i>
                            </button>
                            <span class="w-12 text-center">${item.quantity}</span>
                            <button onclick="cart.updateQuantity(${item.productId}, ${item.quantity + 1})" class="w-8 h-8 border rounded hover:bg-gray-100">
                                <i class="fas fa-plus text-xs"></i>
                            </button>
                            <button onclick="cart.removeFromCart(${item.productId})" class="ml-4 text-red-500 hover:text-red-700">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    <div class="text-right">
                        <p class="font-semibold">${window.Marketplace.formatPrice(item.subtotal)}</p>
                    </div>
                </div>
            </div>
        `).join('');

        cartContainer.innerHTML = itemsHTML;
    }

    updateCartCount(count) {
        const cartCountElements = document.querySelectorAll('#cart-count, #mobile-cart-count');
        cartCountElements.forEach(element => {
            element.textContent = count;
            
            // Add animation
            element.classList.add('animate-bounce');
            setTimeout(() => {
                element.classList.remove('animate-bounce');
            }, 500);
        });
    }

    async syncCartWithServer() {
        try {
            const response = await window.API.safe.cart.get();
            if (response.success) {
                // Update local cart with server data
                this.items = response.articles || [];
                this.total = response.total_panier || 0;
                this.itemCount = response.nombre_articles || 0;
                this.saveCartToStorage();
                this.updateCartUI();
            }
        } catch (error) {
            console.error('Error syncing cart with server:', error);
        }
    }

    clearCart() {
        this.items = [];
        this.total = 0;
        this.itemCount = 0;
        this.saveCartToStorage();
        this.updateCartUI();
    }

    handleEmptyCart() {
        // Show empty cart message or redirect
        if (window.location.pathname.includes('/panier')) {
            // Reload page to show empty cart state
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    }

    dispatchCartEvent(eventType, data = {}) {
        const event = new CustomEvent(`cart:${eventType}`, {
            detail: {
                cart: {
                    items: this.items,
                    total: this.total,
                    itemCount: this.itemCount
                },
                ...data
            }
        });
        document.dispatchEvent(event);
    }

    // Utility methods
    getItems() {
        return [...this.items];
    }

    getTotal() {
        return this.total;
    }

    getItemCount() {
        return this.itemCount;
    }

    isEmpty() {
        return this.items.length === 0;
    }

    getItem(productId) {
        return this.items.find(item => item.productId === productId);
    }

    isInCart(productId) {
        return this.items.some(item => item.productId === productId);
    }
}

// Initialize cart
const cart = new Cart();

// Global functions for backward compatibility
function addToCart(productId, quantity = 1) {
    return cart.addToCart(productId, quantity);
}

function updateQuantity(itemId, newQuantity) {
    return cart.updateQuantity(itemId, newQuantity);
}

function removeFromCart(itemId) {
    return cart.removeFromCart(itemId);
}

function updateCartCount(count) {
    cart.updateCartCount(count);
}

// Export for global use
window.Cart = cart;
window.cart = cart;
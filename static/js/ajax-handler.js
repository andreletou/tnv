class AjaxHandler {
    constructor() {
        this.csrfToken = this.getCSRFToken();
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            credentials: 'same-origin'
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, mergedOptions);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Erreur réseau');
            }
            
            return data;
        } catch (error) {
            console.error('Erreur AJAX:', error);
            this.showNotification(error.message, 'error');
            throw error;
        }
    }

    showNotification(message, type = 'success') {
        // Implémentez votre système de notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.notification-container') || document.body;
        container.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Instance globale
const ajaxHandler = new AjaxHandler();

// Gestionnaire de panier
class PanierManager {
    constructor() {
        this.bindEvents();
        this.updatePanierInfo();
    }

    bindEvents() {
        // Ajouter au panier
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-ajouter-panier')) {
                e.preventDefault();
                this.ajouterAuPanier(e.target.closest('.btn-ajouter-panier'));
            }
        });

        // Modifier quantité
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('quantite-panier')) {
                this.modifierQuantite(e.target);
            }
        });

        // Supprimer du panier
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-supprimer-panier')) {
                e.preventDefault();
                this.supprimerDuPanier(e.target.closest('.btn-supprimer-panier'));
            }
        });
    }

    async ajouterAuPanier(button) {
        const produitId = button.dataset.produitId;
        const quantite = parseInt(button.dataset.quantite || 1);

        try {
            const data = await ajaxHandler.request('/clients/api/panier/ajouter/', {
                method: 'POST',
                body: JSON.stringify({ produit_id: produitId, quantite: quantite })
            });

            if (data.success) {
                this.updatePanierInfo(data);
                ajaxHandler.showNotification(data.message, 'success');
                
                // Mettre à jour le compteur dans le header
                this.updateHeaderPanier(data.nombre_articles, data.total_panier);
            }
        } catch (error) {
            // Gestion d'erreur déjà faite dans request()
        }
    }

    async modifierQuantite(input) {
        const itemId = input.dataset.itemId;
        const quantite = parseInt(input.value);

        try {
            const data = await ajaxHandler.request('/clients/api/panier/modifier/', {
                method: 'POST',
                body: JSON.stringify({ item_id: itemId, quantite: quantite })
            });

            if (data.success) {
                this.updatePanierInfo(data);
                ajaxHandler.showNotification(data.message, 'success');
                
                if (data.article) {
                    // Mettre à jour le sous-total
                    const sousTotalElement = document.querySelector(`.sous-total-${itemId}`);
                    if (sousTotalElement) {
                        sousTotalElement.textContent = `${data.article.sous_total} €`;
                    }
                } else {
                    // Produit retiré, supprimer la ligne
                    const ligneElement = document.querySelector(`.ligne-panier-${itemId}`);
                    if (ligneElement) {
                        ligneElement.remove();
                    }
                }
                
                this.updateHeaderPanier(data.nombre_articles, data.total_panier);
            }
        } catch (error) {
            // Revertir la valeur en cas d'erreur
            input.value = input.dataset.oldValue;
        }
    }

    async supprimerDuPanier(button) {
        const itemId = button.dataset.itemId;

        try {
            const data = await ajaxHandler.request('/clients/api/panier/supprimer/', {
                method: 'POST',
                body: JSON.stringify({ item_id: itemId })
            });

            if (data.success) {
                this.updatePanierInfo(data);
                ajaxHandler.showNotification(data.message, 'success');
                
                // Supprimer la ligne
                const ligneElement = document.querySelector(`.ligne-panier-${itemId}`);
                if (ligneElement) {
                    ligneElement.remove();
                }
                
                this.updateHeaderPanier(data.nombre_articles, data.total_panier);
            }
        } catch (error) {
            // Gestion d'erreur déjà faite dans request()
        }
    }

    updatePanierInfo(data = null) {
        if (data) {
            // Mettre à jour les éléments avec les nouvelles données
            const totalElement = document.querySelector('.total-panier');
            const nombreArticlesElement = document.querySelector('.nombre-articles');
            
            if (totalElement) totalElement.textContent = `${data.total_panier} €`;
            if (nombreArticlesElement) nombreArticlesElement.textContent = data.nombre_articles;
        } else {
            // Récupérer les infos depuis l'API
            this.fetchPanierInfo();
        }
    }

    async fetchPanierInfo() {
        try {
            const data = await ajaxHandler.request('/clients/api/panier/infos/');
            this.updateHeaderPanier(data.nombre_articles, data.total_panier);
        } catch (error) {
            console.error('Erreur lors de la récupération des infos panier:', error);
        }
    }

    updateHeaderPanier(nombreArticles, totalPanier) {
        const badgePanier = document.querySelector('.badge-panier');
        const totalHeader = document.querySelector('.total-panier-header');
        
        if (badgePanier) badgePanier.textContent = nombreArticles;
        if (totalHeader) totalHeader.textContent = `${totalPanier} €`;
    }
}

// Gestionnaire de favoris
class FavorisManager {
    constructor() {
        this.bindEvents();
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-favori')) {
                e.preventDefault();
                this.toggleFavori(e.target.closest('.btn-favori'));
            }
        });
    }

    async toggleFavori(button) {
        const produitId = button.dataset.produitId;
        const estFavori = button.classList.contains('active');

        try {
            const url = estFavori ? 
                '/clients/api/favoris/supprimer/' : 
                '/clients/api/favoris/ajouter/';

            const data = await ajaxHandler.request(url, {
                method: 'POST',
                body: JSON.stringify({ produit_id: produitId })
            });

            if (data.success) {
                button.classList.toggle('active', data.est_favori);
                ajaxHandler.showNotification(data.message, 'success');
                
                // Mettre à jour l'icône
                const icon = button.querySelector('i');
                if (icon) {
                    icon.className = data.est_favori ? 
                        'fas fa-heart' : 
                        'far fa-heart';
                }
            }
        } catch (error) {
            // Gestion d'erreur déjà faite dans request()
        }
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    new PanierManager();
    new FavorisManager();
});
// static/js/utils.js

// Fonction pour récupérer les cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Fonction pour les requêtes AJAX avec CSRF
function makeAjaxRequest(url, data, method = 'POST') {
    return fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify(data)
    });
}

// Fonction pour afficher les notifications
function showToast(message, type = 'info') {
    // Implémentez votre système de notifications
    console.log(`${type.toUpperCase()}: ${message}`);
    alert(message); // Solution temporaire
}
from django import template

register = template.Library()

@register.filter
def selectattr(queryset, attribute):
    """Filtre un queryset par un attribut booléen"""
    if hasattr(queryset, 'filter'):
        # C'est un QuerySet
        filter_kwargs = {attribute: True}
        return queryset.filter(**filter_kwargs)
    else:
        # C'est une liste
        return [item for item in queryset if getattr(item, attribute, False)]

@register.filter
def to_list(queryset):
    """Convertit un QuerySet en liste"""
    return list(queryset)

@register.filter
def calculate_discount(prix_original, prix_promotionnel):
    """
    Calcule le pourcentage de réduction entre le prix original et le prix promotionnel
    """
    try:
        prix_original = float(prix_original)
        prix_promotionnel = float(prix_promotionnel)
        
        if prix_original <= 0:
            return 0
        
        reduction = ((prix_original - prix_promotionnel) / prix_original) * 100
        return round(reduction)
    except (ValueError, TypeError):
        return 0
@register.filter
def format_currency(value):
    """Formate une valeur numérique en une chaîne monétaire avec le symbole '₣'"""
    try:
        value = float(value)
        return f"{value:,.2f} FCFA".replace(',', ' ').replace('.', ',')
    except (ValueError, TypeError):
        return value
@register.filter
def multiply(value, arg):
    """Multiplie la valeur par l'argument donné"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value
@register.filter
def sub(value, arg):
    """Soustrait l'argument de la valeur donnée"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value
@register.filter
def add(value, arg):
    """Ajoute l'argument à la valeur donnée"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def format_price(value):
    """Formate une valeur numérique en une chaîne monétaire avec le symbole '₣'"""
    try:
        value = float(value)
        return f"{value:,.0f} FCFA".replace(',', ' ').replace('.', ',')
    except (ValueError, TypeError):
        return value

@register.filter
def intcomma(value):
    """Convertit une valeur en entier avec des espaces comme séparateurs de milliers"""
    try:
        value = int(value)
        return f"{value:,}".replace(',', ' ')
    except (ValueError, TypeError):
        return value
    
@register.filter
def subtract(value, arg):
    """Soustrait l'argument de la valeur donnée"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def split(value, delimiter=','):
    """Divise une chaîne en une liste en utilisant le délimiteur spécifié"""
    try:
        return value.split(delimiter)
    except AttributeError:
        return value

@register.filter
def category_gradient(category):
    """Retourne une classe de gradient CSS basée sur la catégorie du produit"""
    category_gradients = {
        'Électronique': 'from-blue-400 to-blue-600',
        'Vêtements': 'from-pink-400 to-pink-600',
        'Maison': 'from-green-400 to-green-600',
        'Beauté': 'from-purple-400 to-purple-600',
        'Sports': 'from-yellow-400 to-yellow-600',
    }
    return category_gradients.get(category, 'from-gray-400 to-gray-600')

@register.filter
def category_icon(category):
    """Retourne une icône CSS basée sur la catégorie du produit"""
    category_icons = {
        'Électronique': 'fas fa-tv',
        'Vêtements': 'fas fa-tshirt',
        'Maison': 'fas fa-home',
        'Beauté': 'fas fa-magic',
        'Sports': 'fas fa-football-ball',
    }
    return category_icons.get(category, 'fas fa-box-open')

@register.filter
def category_color_bg(category):
    """Retourne une classe de couleur de fond CSS basée sur la catégorie du produit"""
    category_colors_bg = {
        'Électronique': 'bg-blue-100',
        'Vêtements': 'bg-pink-100',
        'Maison': 'bg-green-100',
        'Beauté': 'bg-purple-100',
        'Sports': 'bg-yellow-100',
    }
    return category_colors_bg.get(category, 'bg-gray-100')

@register.filter
def category_color_text(category):
    """Retourne une classe de couleur de texte CSS basée sur la catégorie du produit"""
    category_colors_text = {
        'Électronique': 'text-blue-600',
        'Vêtements': 'text-pink-600',
        'Maison': 'text-green-600',
        'Beauté': 'text-purple-600',
        'Sports': 'text-yellow-600',
    }
    return category_colors_text.get(category, 'text-gray-600')
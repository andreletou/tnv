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
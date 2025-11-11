from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

class User(AbstractUser):
    TYPE_UTILISATEUR_CHOICES = [
        ('client', 'Client'),
        ('livreur', 'Livreur'),
        ('commercant', 'Commerçant'),
        ('admin', 'Administrateur'),
    ]
    
    type_utilisateur = models.CharField(
        max_length=20, 
        choices=TYPE_UTILISATEUR_CHOICES, 
        default='client'
    )
    telephone = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?228?\d{9,15}$', message="Le numéro de téléphone doit être valide.")],
        blank=True,
        verbose_name="Téléphone"
    )
    photo_profil = models.ImageField(upload_to='profils/', blank=True, null=True)
    adresse = models.TextField(blank=True, verbose_name="Adresse complète")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    sexe = models.CharField(
        max_length=10,
        choices=[('M', 'Masculin'), ('F', 'Féminin'), ('A', 'Autre')],
        null=True,
        blank=True
    )
    consentement_geolocalisation = models.BooleanField(default=False)
    preferences_notifications = models.BooleanField(default=True)
    date_inscription = models.DateTimeField(auto_now_add=True)
    est_actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.username} ({self.get_type_utilisateur_display()})"
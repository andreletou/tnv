from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Livreur, Livraison, EvaluationLivreur

User = get_user_model()

class LivreurInscriptionForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=30, required=True, label="Prénom")
    last_name = forms.CharField(max_length=30, required=True, label="Nom")
    
    # Champs spécifiques au livreur
    telephone = forms.CharField(
        max_length=20,
        required=True,
        label="Téléphone",
        widget=forms.TextInput(attrs={'placeholder': '228 XX XX XX XX'})
    )
    photo_profil = forms.ImageField(
        required=False,
        label="Photo de profil",
        help_text="Format recommandé: carré, minimum 200x200px"
    )
    permis_conduire = forms.ImageField(
        required=True,
        label="Permis de conduire",
        help_text="Photo claire de votre permis de conduire"
    )
    carte_grise = forms.ImageField(
        required=True,
        label="Carte grise",
        help_text="Photo de la carte grise de votre véhicule"
    )
    type_vehicule = forms.ChoiceField(
        choices=[
            ('moto', 'Moto'),
            ('voiture', 'Voiture'),
            ('velo', 'Vélo'),
            ('scooter', 'Scooter'),
        ],
        required=True,
        label="Type de véhicule",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    immatriculation = forms.CharField(
        max_length=20,
        required=True,
        label="Immatriculation du véhicule",
        widget=forms.TextInput(attrs={'placeholder': 'Ex: AA-123-BB'})
    )
    
    # Consentements
    consentement_donnees = forms.BooleanField(
        required=True,
        label="J'accepte que mes données soient utilisées pour la géolocalisation pendant les livraisons"
    )
    consentement_conditions = forms.BooleanField(
        required=True,
        label="J'accepte les conditions générales d'utilisation"
    )
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name', 'password1', 'password2',
            'telephone', 'photo_profil'
        )
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type_vehicule'].widget.attrs.update({'class': 'form-control'})
        self.fields['telephone'].widget.attrs.update({'class': 'form-control'})
        self.fields['immatriculation'].widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.telephone = self.cleaned_data['telephone']
        user.photo_profil = self.cleaned_data['photo_profil']
        user.type_utilisateur = 'livreur'
        
        if commit:
            user.save()
            # Créer le profil livreur
            Livreur.objects.create(
                user=user,
                permis_conduire=self.cleaned_data['permis_conduire'],
                carte_grise=self.cleaned_data['carte_grise'],
                type_vehicule=self.cleaned_data['type_vehicule'],
                immatriculation=self.cleaned_data['immatriculation']
            )
        
        return user

class ProfilLivreurForm(forms.ModelForm):
    """Formulaire pour modifier le profil du livreur"""
    # Champs User
    email = forms.EmailField(label="Email")
    first_name = forms.CharField(max_length=30, label="Prénom")
    last_name = forms.CharField(max_length=30, label="Nom")
    telephone = forms.CharField(max_length=20, label="Téléphone")
    photo_profil = forms.ImageField(required=False, label="Photo de profil")
    
    class Meta:
        model = Livreur
        fields = [
            'type_vehicule', 'immatriculation',
            'est_disponible', 'permis_conduire', 'carte_grise'
        ]
        widgets = {
            'type_vehicule': forms.Select(attrs={'class': 'form-control'}),
            'immatriculation': forms.TextInput(attrs={'class': 'form-control'}),
            'est_disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'permis_conduire': forms.FileInput(attrs={'class': 'form-control'}),
            'carte_grise': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['telephone'].initial = self.instance.user.telephone
            self.fields['photo_profil'].initial = self.instance.user.photo_profil
    
    def save(self, commit=True):
        profil = super().save(commit=False)
        
        # Mettre à jour les informations utilisateur
        if profil.user:
            profil.user.email = self.cleaned_data['email']
            profil.user.first_name = self.cleaned_data['first_name']
            profil.user.last_name = self.cleaned_data['last_name']
            profil.user.telephone = self.cleaned_data['telephone']
            profil.user.photo_profil = self.cleaned_data['photo_profil']
            if commit:
                profil.user.save()
        
        if commit:
            profil.save()
        
        return profil

class PositionForm(forms.Form):
    """Formulaire pour mettre à jour la position du livreur"""
    latitude = forms.DecimalField(
        max_digits=10,
        decimal_places=7,
        required=True,
        widget=forms.HiddenInput()
    )
    longitude = forms.DecimalField(
        max_digits=10,
        decimal_places=7,
        required=True,
        widget=forms.HiddenInput()
    )

class LivraisonForm(forms.ModelForm):
    """Formulaire pour mettre à jour les informations de livraison"""
    
    class Meta:
        model = Livraison
        fields = [
            'instructions_speciales', 'preuve_livraison', 'signature_client'
        ]
        widgets = {
            'instructions_speciales': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Instructions spéciales pour la livraison...'
            }),
            'preuve_livraison': forms.FileInput(attrs={'class': 'form-control'}),
            'signature_client': forms.FileInput(attrs={'class': 'form-control'}),
        }

class EvaluationLivreurForm(forms.ModelForm):
    """Formulaire pour évaluer un livreur"""
    
    class Meta:
        model = EvaluationLivreur
        fields = [
            'note', 'commentaire', 'ponctualite', 'professionalisme', 'securite'
        ]
        widgets = {
            'note': forms.Select(
                choices=[(i, f'{i} étoile{"s" if i > 1 else ""}') for i in range(1, 6)],
                attrs={'class': 'form-control'}
            ),
            'commentaire': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Votre commentaire sur la livraison...'
            }),
            'ponctualite': forms.Select(
                choices=[(i, f'{i}/5') for i in range(1, 6)],
                attrs={'class': 'form-control'}
            ),
            'professionalisme': forms.Select(
                choices=[(i, f'{i}/5') for i in range(1, 6)],
                attrs={'class': 'form-control'}
            ),
            'securite': forms.Select(
                choices=[(i, f'{i}/5') for i in range(1, 6)],
                attrs={'class': 'form-control'}
            ),
        }

class DisponibiliteForm(forms.Form):
    """Formulaire pour gérer la disponibilité du livreur"""
    est_disponible = forms.BooleanField(
        required=False,
        label="Je suis disponible pour les livraisons"
    )
    est_en_ligne = forms.BooleanField(
        required=False,
        label="Je suis en ligne (ma position sera partagée)"
    )

class RechercheLivraisonForm(forms.Form):
    """Formulaire pour rechercher des livraisons disponibles"""
    TYPE_VEHICULE_CHOICES = [
        ('', 'Tous types'),
        ('moto', 'Moto'),
        ('voiture', 'Voiture'),
        ('velo', 'Vélo'),
        ('scooter', 'Scooter'),
    ]
    
    rayon = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=10,
        label="Rayon de recherche (km)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    type_vehicule_preferé = forms.ChoiceField(
        choices=TYPE_VEHICULE_CHOICES,
        required=False,
        label="Type de véhicule préféré",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    montant_minimum = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="Montant minimum de livraison (FCFA)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '100'})
    )
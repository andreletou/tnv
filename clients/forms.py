from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Client, Avis

User = get_user_model()

class ClientInscriptionForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=30, required=True, label="Prénom")
    last_name = forms.CharField(max_length=30, required=True, label="Nom")
    
    # Champs spécifiques au client
    telephone = forms.CharField(
        max_length=20,
        required=True,
        label="Téléphone",
        widget=forms.TextInput(attrs={'placeholder': '228 XX XX XX XX'})
    )
    adresse = forms.CharField(widget=forms.Textarea, required=True, label="Adresse complète")
    photo_profil = forms.ImageField(required=False, label="Photo de profil")
    date_naissance = forms.DateField(
        required=False,
        label="Date de naissance",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    sexe = forms.ChoiceField(
        choices=[('M', 'Masculin'), ('F', 'Féminin'), ('A', 'Autre')],
        required=False,
        label="Sexe"
    )
    preferences_notifications = forms.BooleanField(
        initial=True,
        required=False,
        label="Recevoir des notifications"
    )
    
    consentement_geolocalisation = forms.BooleanField(
        required=False,
        label="Autoriser la géolocalisation pour une livraison plus précise",
        help_text="Nous utiliserons votre position pour calculer les meilleures routes de livraison"
    )
    
    class Meta:
        model = User  # ⚠️ CHANGER ICI : Utiliser User au lieu de Client
        fields = (
            'username', 'email', 'first_name', 'last_name', 'password1', 'password2',
            'telephone', 'adresse', 'photo_profil', 'date_naissance', 'sexe',
            'preferences_notifications', 'consentement_geolocalisation'
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.telephone = self.cleaned_data['telephone']
        user.adresse = self.cleaned_data['adresse']
        user.photo_profil = self.cleaned_data['photo_profil']
        user.date_naissance = self.cleaned_data['date_naissance']
        user.sexe = self.cleaned_data['sexe']
        user.preferences_notifications = self.cleaned_data['preferences_notifications']
        user.consentement_geolocalisation = self.cleaned_data['consentement_geolocalisation']
        user.type_utilisateur = 'client'  # ⚠️ AJOUTER : Définir le type utilisateur
        
        if commit:
            user.save()
            # Créer le profil client associé
            Client.objects.create(user=user)
        
        return user

class ProfilForm(forms.ModelForm):
    consentement_geolocalisation = forms.BooleanField(
        required=False,
        label="Autoriser la géolocalisation pour une livraison plus précise"
    )
    
    # Ajouter les champs utilisateur
    first_name = forms.CharField(max_length=30, required=True, label="Prénom")
    last_name = forms.CharField(max_length=30, required=True, label="Nom")
    email = forms.EmailField(required=True, label="Email")
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'telephone', 'adresse',
            'photo_profil', 'date_naissance', 'sexe', 'preferences_notifications',
            'consentement_geolocalisation'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'photo_profil': forms.FileInput(attrs={'class': 'form-control'}),
            'date_naissance': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'sexe': forms.Select(attrs={'class': 'form-control'}),
            'preferences_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'consentement_geolocalisation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'user'):
            # Si on passe un objet Client, utiliser les données de l'User associé
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        # Si on utilise User directement
        user = super().save(commit=False)
        if commit:
            user.save()
        return user

class AvisForm(forms.ModelForm):
    class Meta:
        model = Avis
        fields = ['note', 'commentaire']
        widgets = {
            'note': forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'form-control'}),
            'commentaire': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
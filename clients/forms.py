from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Client, Avis, RetraitCommercant
from decimal import Decimal

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
        widget=forms.TextInput(attrs={'placeholder': '98 14 48 46'})
    )
    adresse = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}), 
        required=True, 
        label="Adresse complète"
    )
    photo_profil = forms.ImageField(required=False, label="Photo de profil")
    date_naissance = forms.DateField(
        required=False,
        label="Date de naissance",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    sexe = forms.ChoiceField(
        choices=[('', 'Sélectionnez'), ('M', 'Masculin'), ('F', 'Féminin'), ('A', 'Autre')],
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
        label="Autoriser la géolocalisation pour une livraison plus précise"
    )
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name', 'password1', 'password2',
            'telephone', 'adresse', 'photo_profil', 'date_naissance', 'sexe',
            'preferences_notifications', 'consentement_geolocalisation'
        )
    
    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone')
        # Nettoyer le numéro de téléphone
        telephone = telephone.replace(' ', '').replace('-', '')
        if not telephone.isdigit():
            raise forms.ValidationError("Le numéro de téléphone ne doit contenir que des chiffres.")
        return telephone
    
    def save(self, commit=True):
        try:
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
            user.type_utilisateur = 'client'
            
            if commit:
                user.save()
                # Créer le profil client associé
                Client.objects.get_or_create(user=user)
            
            return user
        except Exception as e:
            raise forms.ValidationError(f"Erreur lors de la création du compte: {str(e)}")
        
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

class DepotMobileMoneyForm(forms.Form):
    """Formulaire pour dépôt Mobile Money"""
    montant = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        min_value=100,  # Minimum 100 FCFA
        label="Montant (FCFA)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Montant à déposer'
        })
    )
    operateur = forms.ChoiceField(
        choices=[('', 'Sélectionnez un opérateur'), ('FLOOZ', 'FLOOZ'), ('TMONEY', 'T-Money')],
        label="Opérateur",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    numero_telephone = forms.CharField(
        max_length=20,
        label="Numéro de téléphone",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '90 12 34 56'
        })
    )
    
    def clean_numero_telephone(self):
        numero = self.cleaned_data.get('numero_telephone')
        # Nettoyer le numéro
        numero = numero.replace(' ', '').replace('-', '')
        if not numero.isdigit():
            raise forms.ValidationError("Le numéro de téléphone ne doit contenir que des chiffres.")
        return numero

class DepotPayGateForm(forms.Form):
    """Formulaire pour dépôt via PayGate"""
    montant = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        min_value=100,
        label="Montant (FCFA)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Montant à déposer'
        })
    )

class DemandeRetraitForm(forms.ModelForm):
    class Meta:
        model = RetraitCommercant
        fields = ['montant', 'methode', 'operateur', 'numero_compte', 'nom_beneficiaire']
    
    def __init__(self, *args, **kwargs):
        self.portefeuille = kwargs.pop('portefeuille')
        super().__init__(*args, **kwargs)
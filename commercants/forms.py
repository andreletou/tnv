from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Commercant, Produit, Promotion

User = get_user_model()

class CommercantInscriptionForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=30, required=True, label="Prénom")
    last_name = forms.CharField(max_length=30, required=True, label="Nom")
    
    # Champs spécifiques au commerçant
    nom_boutique = forms.CharField(max_length=200, required=True, label="Nom de la boutique")
    categorie = forms.ChoiceField(choices=Commercant.CATEGORIES, required=True, label="Catégorie")
    telephone = forms.CharField(
        max_length=20,
        required=True,
        label="Téléphone",
        widget=forms.TextInput(attrs={'placeholder': '228 XX XX XX XX'})
    )
    adresse = forms.CharField(widget=forms.Textarea, required=True, label="Adresse complète")
    description = forms.CharField(widget=forms.Textarea, required=False, label="Description de la boutique")
    photo_boutique = forms.ImageField(required=False, label="Photo de la boutique")
    horaire_ouverture = forms.TimeField(required=True, label="Heure d'ouverture")
    horaire_fermeture = forms.TimeField(required=True, label="Heure de fermeture")
    jours_ouverture = forms.CharField(
        max_length=100,
        initial="Lundi-Mardi-Mercredi-Jeudi-Vendredi-Samedi",
        required=True,
        label="Jours d'ouverture"
    )
    
    class Meta:
        model = User  # ⚠️ CHANGER ICI : Utiliser User au lieu de Commercant
        fields = (
            'username', 'email', 'first_name', 'last_name', 'password1', 'password2',
            'telephone', 'adresse'  # ⚠️ AJOUTER les champs User
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.telephone = self.cleaned_data['telephone']
        user.adresse = self.cleaned_data['adresse']
        user.type_utilisateur = 'commercant'  # ⚠️ AJOUTER : Définir le type utilisateur
        user.is_staff = True  # Marquer comme commerçant
        
        if commit:
            user.save()
            # Créer le profil commerçant
            Commercant.objects.create(
                user=user,
                nom_boutique=self.cleaned_data['nom_boutique'],
                categorie=self.cleaned_data['categorie'],
                description=self.cleaned_data['description'],
                photo_boutique=self.cleaned_data['photo_boutique'],
                horaire_ouverture=self.cleaned_data['horaire_ouverture'],
                horaire_fermeture=self.cleaned_data['horaire_fermeture'],
                jours_ouverture=self.cleaned_data['jours_ouverture']
            )
        
        return user

class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = [
            'nom', 'description', 'prix', 'prix_promotionnel', 'stock', 'stock_min',
            'categorie', 'photo', 'est_actif', 'est_en_promotion'
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'prix': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'prix_promotionnel': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'min': '0', 'class': 'form-control'}),
            'stock_min': forms.NumberInput(attrs={'min': '0', 'class': 'form-control'}),
            'categorie': forms.Select(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'est_en_promotion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_prix_promotionnel(self):
        prix = self.cleaned_data.get('prix')
        prix_promotionnel = self.cleaned_data.get('prix_promotionnel')
        
        if prix_promotionnel and prix_promotionnel >= prix:
            raise forms.ValidationError("Le prix promotionnel doit être inférieur au prix normal.")
        
        return prix_promotionnel

class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ['produit', 'pourcentage_reduction', 'date_debut', 'date_fin', 'description', 'est_active']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-control'}),
            'pourcentage_reduction': forms.NumberInput(attrs={'min': '1', 'max': '90', 'class': 'form-control'}),
            'date_debut': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'date_fin': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'est_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        commercant = kwargs.pop('commercant', None)
        super().__init__(*args, **kwargs)
        
        if commercant:
            self.fields['produit'].queryset = Produit.objects.filter(commercant=commercant)
    
    def clean_pourcentage_reduction(self):
        pourcentage = self.cleaned_data.get('pourcentage_reduction')
        
        if pourcentage < 1 or pourcentage > 90:
            raise forms.ValidationError("Le pourcentage de réduction doit être entre 1% et 90%.")
        
        return pourcentage
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin and date_debut >= date_fin:
            raise forms.ValidationError("La date de fin doit être postérieure à la date de début.")
        
        return cleaned_data

class ProfilForm(forms.ModelForm):
    # Champs utilisateur
    first_name = forms.CharField(max_length=30, label="Prénom")
    last_name = forms.CharField(max_length=30, label="Nom")
    email = forms.EmailField(label="Email")
    telephone = forms.CharField(max_length=20, label="Téléphone")  # ⚠️ AJOUTER
    adresse = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label="Adresse complète")  # ⚠️ AJOUTER
    
    class Meta:
        model = Commercant
        fields = [
            'nom_boutique', 'categorie', 'description',
            'photo_boutique', 'horaire_ouverture', 'horaire_fermeture', 
            'jours_ouverture', 'est_actif'
        ]
        widgets = {
            'nom_boutique': forms.TextInput(attrs={'class': 'form-control'}),
            'categorie': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'photo_boutique': forms.FileInput(attrs={'class': 'form-control'}),
            'horaire_ouverture': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horaire_fermeture': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'jours_ouverture': forms.TextInput(attrs={'class': 'form-control'}),
            'est_actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            self.fields['telephone'].initial = self.instance.user.telephone  # ⚠️ AJOUTER
            self.fields['adresse'].initial = self.instance.user.adresse  # ⚠️ AJOUTER
    
    def save(self, commit=True):
        profil = super().save(commit=False)
        
        # Mettre à jour les informations utilisateur
        if profil.user:
            profil.user.first_name = self.cleaned_data['first_name']
            profil.user.last_name = self.cleaned_data['last_name']
            profil.user.email = self.cleaned_data['email']
            profil.user.telephone = self.cleaned_data['telephone']
            profil.user.adresse = self.cleaned_data['adresse']
            if commit:
                profil.user.save()
        
        if commit:
            profil.save()
        
        return profil
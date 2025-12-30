# client/paygate.py
import requests
import json
from django.conf import settings

class PayGateGlobal:
    """
    Classe corrigée pour PayGateGlobal selon la documentation
    """
    
    API_URL = "https://paygateglobal.com/api/v1/pay"
    STATUS_URL_IDENTIFIER = "https://paygateglobal.com/api/v2/status"
    STATUS_URL_TX_REFERENCE = "https://paygateglobal.com/api/v1/status"
    PAGE_URL = "https://paygateglobal.com/v1/page"
    AUTH_TOKEN = "9498ec13-33e9-4f53-bfa2-66e95e5bdc08"
    
    @classmethod
    def initier_paiement_api(cls, phone_number, amount, description, identifier, network):
        """
        Méthode 1 améliorée avec gestion d'erreurs
        """
        try:
            # Validation des paramètres
            if not all([phone_number, amount, identifier, network]):
                return {"status": "error", "message": "Paramètres manquants"}
            
            # Nettoyer le numéro de téléphone
            phone_number = ''.join(filter(str.isdigit, phone_number))
            
            # Convertir le montant
            try:
                amount_int = int(float(amount))
                if amount_int <= 0:
                    return {"status": "error", "message": "Montant invalide"}
            except (ValueError, TypeError):
                return {"status": "error", "message": "Montant invalide"}
            
            data = {
                "auth_token": cls.AUTH_TOKEN,
                "phone_number": phone_number,
                "amount": amount_int,
                "description": description[:255],  # Limiter la longueur
                "identifier": identifier,
                "network": network.upper()
            }
            
            print(f"📤 PayGate Request: {data}")
            
            response = requests.post(cls.API_URL, json=data, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            
            print(f"📥 PayGate Response: {response_data}")
            return response_data
            
        except requests.exceptions.Timeout:
            return {"status": "error", "message": "Timeout de connexion à PayGate"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Erreur réseau: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": f"Erreur inattendue: {str(e)}"}
    @classmethod
    def verifier_statut_par_identifier(cls, identifier):
        """
        Vérifier le statut par VOTRE identifiant (ex: "DEP-1-ABC123")
        URL: https://paygateglobal.com/api/v2/status
        """
        data = {
            "auth_token": cls.AUTH_TOKEN,
            "identifier": identifier
        }
        
        print(f"🔍 Vérification par identifier: {identifier}")
        
        try:
            response = requests.post(cls.STATUS_URL_IDENTIFIER, json=data, timeout=30)
            result = response.json()
            print(f"📥 Réponse par identifier: {result}")
            return result
        except Exception as e:
            print(f"❌ Erreur vérification identifier: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    @classmethod
    def verifier_statut_par_tx_reference(cls, tx_reference):
        """
        Vérifier le statut par TX_REFERENCE PayGate (ex: "CMD-3-7D58C6F8")
        URL: https://paygateglobal.com/api/v1/status
        """
        data = {
            "auth_token": cls.AUTH_TOKEN,
            "tx_reference": tx_reference
        }
        
        print(f"🔍 Vérification par tx_reference: {tx_reference}")
        
        try:
            response = requests.post(cls.STATUS_URL_TX_REFERENCE, json=data, timeout=30)
            result = response.json()
            print(f"📥 Réponse par tx_reference: {result}")
            return result
        except Exception as e:
            print(f"❌ Erreur vérification tx_reference: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    @classmethod
    def generer_lien_paiement(cls, amount, description, identifier, redirect_url=None):
        """
        Méthode 2: Générer un lien de paiement pour redirection
        """
        params = {
            "token": cls.AUTH_TOKEN,
            "amount": str(int(float(amount))),  # Montant sans décimales
            "description": description,
            "identifier": identifier
        }
        
        if redirect_url:
            params["url"] = redirect_url
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        payment_url = f"{cls.PAGE_URL}?{query_string}"
        
        print(f"🔗 Lien de paiement généré: {payment_url}")
        return payment_url

    
    @classmethod
    def verifier_statut_paiement(cls, reference):
        """
        Méthode intelligente qui essaie les deux types de référence
        """
        print(f"🔍 Vérification intelligente pour: {reference}")
        
        # Si c'est une référence numérique (comme 5205420), c'est une tx_reference PayGate
        if str(reference).isdigit():
            print("🔄 Détecté comme tx_reference PayGate (numérique)")
            result = cls.verifier_statut_par_tx_reference(reference)
        else:
            print("🔄 Détecté comme identifier interne")
            result = cls.verifier_statut_par_identifier(reference)
        
        status = result.get('status')
        if status == 0:
            result['status_label'] = 'paye'
            result['message'] = 'Paiement réussi'
        elif status == 2:
            result['status_label'] = 'en_attente'
            result['message'] = 'Paiement en cours'
        elif status == 4:
            result['status_label'] = 'expire'
            result['message'] = 'Paiement expiré'
        elif status == 6:
            result['status_label'] = 'annule'
            result['message'] = 'Paiement annulé'
        else:
            result['status_label'] = 'inconnu'
            result['message'] = f'Statut inconnu: {status}'
        
        print(f"📊 Statut interprété: {result['status_label']} (code: {status})")
        return result


    @classmethod
    def verifier_statut_paiement_commande(cls, commande):
        """
        Vérifier le statut d'un objet commande spécifique
        """
        print(f"🔍 Vérification détaillée pour la commande: {commande.reference}")
        
        # Essayer avec tx_reference d'abord
        if commande.paygate_reference:
            result = cls.verifier_statut_par_tx_reference(commande.paygate_reference)
            if result.get('status') in [0, 2, 4, 6]:
                return result
        
        # Essayer avec identifier
        result = cls.verifier_statut_par_identifier(commande.reference)
        return result
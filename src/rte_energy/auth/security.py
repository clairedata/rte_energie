"""
================================================================================
  MODULE : src/rte_energy/auth/security.py
  OBJECTIF : Sécurité cryptographique, hashage des mots de passe (bcrypt)
             et gestion complète du cycle de vie des JSON Web Tokens (JWT).
================================================================================
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt  # Bibliothèque pyjwt pour l'encodage et le décodage des tokens
import bcrypt  # Bibliothèque standard de hashage sécurisé de mots de passe

# ==============================================================================
# 1. PARAMÈTRES DE SÉCURITÉ DU PROTOCOLE JWT
# ==============================================================================

# Clé secrète utilisée pour signer cryptographiquement le JWT.
# IMPORTANT : En production, cette clé DOIT être définie via la variable d'environnement JWT_SECRET_KEY.
# La signature garantit qu'un tiers ne peut pas altérer le contenu du token (par exemple changer son rôle).
SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "rte_energy_secret_key_super_secure_2026_change_in_prod")

# Algorithme de signature symétrique HMAC avec fonction de hachage SHA-256.
# C'est le standard industriel le plus robuste et rapide pour les applications web.
ALGORITHM: str = "HS256"

# Durée de validité du jeton d'accès avant expiration automatique (en minutes).
# Une durée courte limite les risques en cas de vol de jeton.
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))


# ==============================================================================
# 2. FONCTIONS DE HACHAGE ET VÉRIFICATION DES MOTS DE PASSE
# ==============================================================================

def hash_password(password: str) -> str:
    """
    Transforme un mot de passe en clair en une empreinte sécurisée non réversible (hash bcrypt).
    
    Fonctionnement :
    - Génère un 'sel' aléatoire (salt) pour se prémunir des attaques par dictionnaires/tables arc-en-ciel.
    - Applique l'algorithme de hachage itératif bcrypt.
    
    :param password: Mot de passe en clair saisi par l'utilisateur.
    :return: Empreinte hachée (stockable en base de données).
    """
    # Conversion de la chaîne de caractères en octets (bytes UTF-8)
    password_bytes = password.encode("utf-8")
    # Génération du sel aléatoire
    salt = bcrypt.gensalt()
    # Hachage sécurisé
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    # Retour sous forme de chaîne de caractères lisible
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si le mot de passe fourni correspond au hash stocké en base de données.
    
    :param plain_password: Mot de passe en clair soumis lors de la connexion.
    :param hashed_password: Hash bcrypt stocké dans PostgreSQL.
    :return: True si le mot de passe est valide, False sinon.
    """
    try:
        plain_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        # bcrypt.checkpw extrait le sel du hash et recalcule l'empreinte pour comparer en temps constant
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


# ==============================================================================
# 3. CRÉATION ET SIGNATURE DU TOKEN JWT
# ==============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Génère et signe un jeton d'accès JWT contenant les informations de l'utilisateur (Claims).
    
    Structure d'un JWT :
    1. Header : Spécifie l'algorithme (HS256) et le type (JWT).
    2. Payload (Charge utile) : Contient les données métier (email, rôle, id utilisateur)
       ainsi que les métadonnées de sécurité (exp = date d'expiration, iat = date d'émission).
    3. Signature : Calculée avec la clé secrète pour rendre le token infalsifiable.
    
    :param data: Dictionnaire des informations à embarquer dans le payload du token.
    :param expires_delta: Durée de validité personnalisée (optionnelle).
    :return: Chaîne de caractères JWT encodée prête à être transmise au client.
    """
    # Copie défensive des données utilisateur pour ne pas altérer le dictionnaire original
    to_encode = data.copy()

    # Définition de la date et heure d'expiration du jeton (en temps universel UTC)
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Ajout des claims standards recommandés par la RFC 7519 :
    # 'exp' (Expiration Time) : Timestamp Unix après lequel le token est rejeté
    # 'iat' (Issued At) : Timestamp Unix d'émission du token
    to_encode.update({
        "exp": expire,
        "iat": now
    })

    # Encodage et signature cryptographique du JWT avec la clé secrète
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ==============================================================================
# 4. DÉCODAGE ET VALIDATION DU TOKEN JWT
# ==============================================================================

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Décode, vérifie la signature cryptographique et contrôle la validité temporelle d'un JWT.
    
    Vérifications effectuées automatiquement par pyjwt :
    1. La signature est-elle valide (produite avec notre SECRET_KEY et l'algo HS256) ?
    2. Le token est-il encore valide dans le temps (date 'exp' non dépassée) ?
    
    :param token: Le jeton JWT brut reçu dans l'en-tête HTTP 'Authorization: Bearer <token>'.
    :return: Le dictionnaire (payload) extrait du jeton.
    :raises jwt.ExpiredSignatureError: Si le jeton est expiré dans le temps.
    :raises jwt.InvalidTokenError: Si la signature est corrompue, modifiée ou invalide.
    """
    # jwt.decode vérifie automatiquement la signature et le champ 'exp'
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload

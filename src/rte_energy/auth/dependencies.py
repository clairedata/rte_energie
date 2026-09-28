"""
================================================================================
  MODULE : src/rte_energy/auth/dependencies.py
  OBJECTIF : Modèles de données Pydantic, extraction du JWT depuis les requêtes HTTP,
             vérification de l'identité et contrôle d'accès basé sur les rôles (RBAC).
================================================================================
"""

from typing import List, Optional, Dict, Any, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
import jwt
import psycopg2.extras

from rte_energy.config import get_db_connection
from rte_energy.auth.security import decode_access_token
from rte_energy.auth.db_init import ensure_users_table_exists


# ==============================================================================
# 1. MODÈLES DE DONNÉES PYDANTIC (SCHÉMAS DE VALIDATION)
# ==============================================================================

class UserRole:
    """Constantes définissant la hiérarchie des rôles dans la plateforme RTE."""
    VIEWER = "viewer"     # Consultation des courbes et KPIs publics
    ANALYST = "analyst"   # Export des prévisions, analyse fine des modèles IA
    ADMIN = "admin"       # Gestion utilisateurs, déclenchement pipelines MLOps


class Token(BaseModel):
    """Schéma de réponse envoyé au client après une authentification réussie."""
    access_token: str       # Le jeton JWT encodé
    token_type: str = "bearer"  # Type de token standard (Bearer)
    expires_in_minutes: int # Durée avant expiration
    role: str               # Rôle attribué à l'utilisateur
    email: str              # Adresse email de l'utilisateur
    full_name: Optional[str] = None


class TokenPayload(BaseModel):
    """Structure des données internes décodées depuis le payload du JWT."""
    sub: Optional[str] = None  # Subject standard (ici, l'email ou l'ID de l'utilisateur)
    role: Optional[str] = None # Rôle embarqué dans le token
    user_id: Optional[int] = None


class UserResponse(BaseModel):
    """Schéma de données d'un utilisateur renvoyé par l'API (sans mot de passe)."""
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool


class UserCreate(BaseModel):
    """Schéma pour l'inscription ou la création d'un nouvel utilisateur."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = UserRole.VIEWER


class LoginRequest(BaseModel):
    """Schéma pour une connexion au format JSON depuis le frontend React."""
    email: str
    password: str


# ==============================================================================
# 2. SCHÉMA D'EXTRACTION DU TOKEN OAUTH2 / HTTP BEARER
# ==============================================================================

# OAuth2PasswordBearer indique à FastAPI d'inspecter l'en-tête HTTP 'Authorization: Bearer <token>'
# Il fournit également l'intégration automatique dans la documentation interactive Swagger UI (/docs).
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    description="Authentification JWT via en-tête 'Authorization: Bearer <token>'"
)


# ==============================================================================
# 3. DÉPENDANCE FASTAPI : RÉCUPÉRATION DE L'UTILISATEUR COURANT
# ==============================================================================

def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Intercepte chaque requête protégée, décode le token JWT, vérifie son authenticité
    et récupère le profil de l'utilisateur depuis la base PostgreSQL.
    
    Étapes de vérification :
    1. Extraction du token de l'en-tête Authorization.
    2. Décodage cryptographique et vérification de la signature + expiration.
    3. Recherche de l'utilisateur dans la table 'users'.
    4. Contrôle de l'état d'activation du compte ('is_active').
    
    :param token: Le jeton JWT extrait automatiquement par Depends(oauth2_scheme).
    :return: Dictionnaire des informations de l'utilisateur authentifié.
    :raises HTTPException 401: Si le token est invalide, corrompu ou expiré.
    :raises HTTPException 403: Si le compte est désactivé.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants d'authentification invalides ou session expirée.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Étape 1 : Décodage cryptographique du JWT
        payload = decode_access_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        # Le token a dépassé sa date 'exp'
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Votre session a expiré. Veuillez vous reconnecter.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        # La signature est invalide ou le token est altéré
        raise credentials_exception

    # Étape 2 : Vérification de l'existence de l'utilisateur en base de données
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        try:
            cur.execute("""
                SELECT id, email, full_name, role, is_active 
                FROM public.users 
                WHERE email = %s;
            """, (email,))
            user_row = cur.fetchone()
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            ensure_users_table_exists()
            cur.execute("""
                SELECT id, email, full_name, role, is_active 
                FROM public.users 
                WHERE email = %s;
            """, (email,))
            user_row = cur.fetchone()

        if user_row is None:
            raise credentials_exception
        
        user = dict(user_row)
        # Étape 3 : Contrôle de l'état actif du compte
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce compte utilisateur a été désactivé par un administrateur."
            )
        return user
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 4. CONTRÔLE D'ACCÈS BASÉ SUR LES RÔLES (RBAC - ROLE-BASED ACCESS CONTROL)
# ==============================================================================

def require_roles(allowed_roles: List[str]) -> Callable:
    """
    Factory de dépendance FastAPI permettant de restreindre l'accès à un endpoint
    selon une liste de rôles autorisés.
    
    Exemple d'utilisation sur un endpoint :
        @app.post("/api/admin/pipeline")
        def run_pipeline(user = Depends(require_roles(["admin"]))):
            ...
            
    :param allowed_roles: Liste des rôles ayant l'autorisation d'exécuter la route.
    :return: Fonction de dépendance injectable dans FastAPI.
    """
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role")
        # Si le rôle de l'utilisateur connecté ne fait pas partie des rôles autorisés -> 403 Forbidden
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé : votre rôle ({user_role}) n'a pas les permissions requises ({', '.join(allowed_roles)})."
            )
        return current_user

    return role_checker

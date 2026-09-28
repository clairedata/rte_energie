/**
 * ==============================================================================
 * MODULE TYPESCRIPT : frontend/src/types/auth.ts
 * OBJECTIF : Types stricts pour l'authentification JWT et le RBAC côté client.
 * ==============================================================================
 */

/**
 * Rôles disponibles dans le système de permissions RTE Energy.
 */
export type UserRole = "viewer" | "analyst" | "admin";

/**
 * Profil de l'utilisateur renvoyé par le backend après vérification du JWT.
 */
export interface User {
    id: number;
    email: string;
    full_name?: string | null;
    role: UserRole;
    is_active: boolean;
    created_at?: string;
}

/**
 * Réponse du backend lors d'un appel réussi à POST /api/auth/login.
 */
export interface LoginResponse {
    access_token: string;       // Le jeton JWT brut signé par le backend
    token_type: string;         // 'bearer'
    expires_in_minutes: number; // Durée de validité
    role: UserRole;             // Rôle pour le conditionnement d'interface
    email: string;              // Email de l'utilisateur
    full_name?: string | null;  // Nom complet
}

/**
 * État global de l'authentification exposé par le AuthContext React.
 */
export interface AuthContextType {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
    logout: () => void;
    hasRole: (allowedRoles: UserRole[]) => boolean;
}

/**
 * ==============================================================================
 * MODULE REACT : frontend/src/context/AuthContext.tsx
 * OBJECTIF : Fournisseur de contexte global d'authentification JWT & RBAC.
 *            Gère l'état de connexion, l'inscription et le contrôle des rôles.
 * ==============================================================================
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { User, UserRole, AuthContextType } from "../types/auth";
import {
    getStoredToken,
    getStoredUser,
    setStoredSession,
    clearStoredSession,
    loginApi,
    registerApi,
    getMeApi
} from "../services/auth";

export interface ExtendedAuthContextType extends AuthContextType {
    register: (email: string, password: string, fullName?: string, role?: UserRole) => Promise<{ success: boolean; message?: string; error?: string }>;
}

const AuthContext = createContext<ExtendedAuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(getStoredUser());
    const [token, setToken] = useState<string | null>(getStoredToken());
    const [isLoading, setIsLoading] = useState<boolean>(true);

    // Initialisation au montage du composant : vérification de la validité du token stocké
    useEffect(() => {
        const verifySession = async () => {
            const savedToken = getStoredToken();
            if (!savedToken) {
                setIsLoading(false);
                return;
            }

            try {
                const liveUser = await getMeApi(savedToken);
                setUser(liveUser);
                setToken(savedToken);
            } catch (err) {
                console.warn("Session expirée ou invalide, déconnexion automatique :", err);
                clearStoredSession();
                setUser(null);
                setToken(null);
            } finally {
                setIsLoading(false);
            }
        };

        verifySession();
    }, []);

    // Fonction de connexion utilisateur
    const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
        setIsLoading(true);
        try {
            const data = await loginApi(email, password);

            const loggedUser: User = {
                id: 0,
                email: data.email,
                full_name: data.full_name,
                role: data.role,
                is_active: true
            };

            setStoredSession(data.access_token, loggedUser);
            setToken(data.access_token);
            setUser(loggedUser);

            try {
                const fullUser = await getMeApi(data.access_token);
                setUser(fullUser);
                setStoredSession(data.access_token, fullUser);
            } catch {
                // Fallback sur loggedUser
            }

            return { success: true };
        } catch (err: any) {
            return {
                success: false,
                error: err.message || "Erreur de connexion au serveur."
            };
        } finally {
            setIsLoading(false);
        }
    };

    // Fonction d'inscription (compte créé inactif en attente d'approbation)
    const register = async (email: string, password: string, fullName?: string, role: UserRole = "viewer"): Promise<{ success: boolean; message?: string; error?: string }> => {
        try {
            const res = await registerApi(email, password, fullName, role);
            return { success: true, message: res.message };
        } catch (err: any) {
            return { success: false, error: err.message || "Erreur lors de l'inscription." };
        }
    };

    // Fonction de déconnexion
    const logout = useCallback(() => {
        clearStoredSession();
        setUser(null);
        setToken(null);
    }, []);

    // Contrôle d'accès RBAC
    const hasRole = useCallback((allowedRoles: UserRole[]): boolean => {
        if (!user) return false;
        return allowedRoles.includes(user.role);
    }, [user]);

    return (
        <AuthContext.Provider
            value={{
                user,
                token,
                isLoading,
                isAuthenticated: !!token && !!user,
                login,
                register,
                logout,
                hasRole
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = (): ExtendedAuthContextType => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth doit être utilisé à l'intérieur d'un <AuthProvider />");
    }
    return context;
};

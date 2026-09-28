/**
 * ==============================================================================
 * MODULE TYPESCRIPT : frontend/src/services/auth.ts
 * OBJECTIF : Service client pour la communication avec l'API d'authentification,
 *            le stockage du JWT, l'approbation admin, les exports CSV et pipelines.
 * ==============================================================================
 */

import type { LoginResponse, User, UserRole } from "../types/auth";

const TOKEN_STORAGE_KEY = "rte_energy_jwt_token";
const USER_STORAGE_KEY = "rte_energy_user_profile";

/**
 * Récupère le token JWT sauvegardé dans le stockage local du navigateur.
 */
export function getStoredToken(): string | null {
    try {
        return localStorage.getItem(TOKEN_STORAGE_KEY);
    } catch {
        return null;
    }
}

/**
 * Récupère le profil utilisateur sauvegardé dans le stockage local.
 */
export function getStoredUser(): User | null {
    try {
        const raw = localStorage.getItem(USER_STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

/**
 * Sauvegarde le JWT et les données utilisateur lors d'une connexion réussie.
 */
export function setStoredSession(token: string, user: User): void {
    try {
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    } catch (e) {
        console.error("Erreur lors de la sauvegarde de la session :", e);
    }
}

/**
 * Efface le token et la session lors de la déconnexion.
 */
export function clearStoredSession(): void {
    try {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        localStorage.removeItem(USER_STORAGE_KEY);
    } catch (e) {
        console.error("Erreur lors du nettoyage de la session :", e);
    }
}

/**
 * Génère les en-têtes HTTP incluant le Bearer Token JWT pour sécuriser les appels API.
 */
export function getAuthHeaders(): HeadersInit {
    const token = getStoredToken();
    const headers: Record<string, string> = {
        "Content-Type": "application/json"
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    return headers;
}

/**
 * Appel API de connexion.
 */
export async function loginApi(email: string, password: string): Promise<LoginResponse> {
    const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Erreur de connexion" }));
        throw new Error(err.detail || `Échec de l'authentification (${response.status})`);
    }

    return response.json();
}

/**
 * Appel API d'inscription (compte créé inactif en attente d'approbation admin).
 */
export async function registerApi(email: string, password: string, fullName?: string, role: UserRole = "viewer"): Promise<{ user: User; message: string }> {
    const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            email,
            password,
            full_name: fullName,
            role
        })
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Erreur lors de l'inscription" }));
        throw new Error(err.detail || `Échec de l'inscription (${response.status})`);
    }

    return response.json();
}

/**
 * Récupère les informations actualisées de l'utilisateur connecté via /api/auth/me.
 */
export async function getMeApi(token: string): Promise<User> {
    const response = await fetch("/api/auth/me", {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });

    if (!response.ok) {
        throw new Error("Token expiré ou invalide");
    }

    return response.json();
}

/**
 * [ADMIN] Met à jour le statut actif/inactif d'un utilisateur (approbation) ou son rôle.
 */
export async function updateUserStatusApi(userId: number, isActive: boolean, role?: string): Promise<any> {
    const response = await fetch(`/api/admin/users/${userId}/status`, {
        method: "PUT",
        headers: getAuthHeaders(),
        body: JSON.stringify({
            is_active: isActive,
            role: role
        })
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Erreur de mise à jour" }));
        throw new Error(err.detail || `Erreur ${response.status}`);
    }

    return response.json();
}

/**
 * [ADMIN] Déclenche une étape de pipeline (ingestion_rte, ingestion_weather, dbt_run, full_pipeline).
 */
export async function triggerPipelineApi(type: string): Promise<any> {
    const response = await fetch(`/api/admin/trigger-pipeline?pipeline_type=${type}`, {
        method: "POST",
        headers: getAuthHeaders()
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Erreur de pipeline" }));
        throw new Error(err.detail || `Erreur ${response.status}`);
    }

    return response.json();
}

/**
 * [ANALYSTE & ADMIN] Télécharge directement le fichier CSV des prévisions et résidus.
 */
export async function downloadMetricsCsv(): Promise<void> {
    const token = getStoredToken();
    const headers: Record<string, string> = {};
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch("/api/analyst/export-metrics-csv", { headers });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Erreur de téléchargement" }));
        throw new Error(err.detail || `Erreur ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rte_energy_forecasts_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

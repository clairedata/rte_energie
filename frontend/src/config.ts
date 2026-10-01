/**
 * Configuration globale du Frontend :
 * - Si VITE_API_URL est défini dans l'environnement Vercel (ex: https://mon-backend.onrender.com),
 *   les requêtes pointeront vers ce backend distant.
 * - Sinon, chaîne vide "" pour utiliser le chemin relatif local (/api/...).
 */
export const API_BASE_URL: string = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

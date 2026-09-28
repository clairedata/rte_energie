import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { Lock, Mail, AlertCircle, X, Shield, BarChart3, Eye, CheckCircle2, UserPlus, User, Clock } from "lucide-react";
import type { UserRole } from "../types/auth";

interface LoginModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose }) => {
    const { login, register } = useAuth();
    const [mode, setMode] = useState<"login" | "register">("login");
    
    // États du formulaire
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [fullName, setFullName] = useState("");
    const [requestedRole, setRequestedRole] = useState<UserRole>("viewer");

    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    if (!isOpen) return null;

    const handleLoginSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccessMessage(null);
        setIsSubmitting(true);

        const result = await login(email, password);
        setIsSubmitting(false);

        if (result.success) {
            setSuccessMessage("Authentification réussie !");
            setTimeout(() => {
                onClose();
            }, 600);
        } else {
            setError(result.error || "Identifiants invalides");
        }
    };

    const handleRegisterSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccessMessage(null);
        setIsSubmitting(true);

        const result = await register(email, password, fullName, requestedRole);
        setIsSubmitting(false);

        if (result.success) {
            setSuccessMessage(result.message || "Compte créé avec succès ! En attente d'approbation par un administrateur.");
            // Réinitialiser le formulaire
            setEmail("");
            setPassword("");
            setFullName("");
        } else {
            setError(result.error || "Erreur lors de l'inscription.");
        }
    };

    // Connexion rapide 1-clic pour tester
    const handleQuickLogin = async (demoEmail: string, demoPass: string) => {
        setMode("login");
        setEmail(demoEmail);
        setPassword(demoPass);
        setError(null);
        setIsSubmitting(true);

        const result = await login(demoEmail, demoPass);
        setIsSubmitting(false);

        if (result.success) {
            setSuccessMessage(`Connecté avec succès !`);
            setTimeout(() => {
                onClose();
            }, 600);
        } else {
            setError(result.error || "Erreur de connexion");
        }
    };

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-container" onClick={(e) => e.stopPropagation()}>
                {/* En-tête de la modale */}
                <div className="modal-header">
                    <div className="modal-title-group">
                        <div className="modal-icon-wrapper">
                            {mode === "login" ? <Lock size={20} className="modal-icon" /> : <UserPlus size={20} className="modal-icon" />}
                        </div>
                        <div>
                            <h3 className="modal-title">
                                {mode === "login" ? "Espace Authentification" : "Créer un Nouveau Compte"}
                            </h3>
                            <p className="modal-subtitle">
                                {mode === "login" ? "Accès sécurisé par jetons JWT & RBAC" : "Inscription soumise à validation par l'administrateur"}
                            </p>
                        </div>
                    </div>
                    <button className="modal-close-btn" onClick={onClose} aria-label="Fermer">
                        <X size={18} />
                    </button>
                </div>

                {/* Onglets Connexion / Inscription */}
                <div className="auth-tab-group">
                    <button
                        type="button"
                        className={`auth-tab-btn ${mode === "login" ? "active" : ""}`}
                        onClick={() => { setMode("login"); setError(null); setSuccessMessage(null); }}
                    >
                        <Lock size={14} />
                        <span>Se connecter</span>
                    </button>
                    <button
                        type="button"
                        className={`auth-tab-btn ${mode === "register" ? "active" : ""}`}
                        onClick={() => { setMode("register"); setError(null); setSuccessMessage(null); }}
                    >
                        <UserPlus size={14} />
                        <span>S'inscrire</span>
                    </button>
                </div>

                {/* Alertes d'état */}
                {error && (
                    <div className="auth-alert alert-error">
                        <AlertCircle size={16} />
                        <span>{error}</span>
                    </div>
                )}

                {successMessage && (
                    <div className="auth-alert alert-success">
                        <CheckCircle2 size={16} />
                        <span>{successMessage}</span>
                    </div>
                )}

                {/* 1. Formulaire de Connexion */}
                {mode === "login" ? (
                    <form onSubmit={handleLoginSubmit} className="auth-form">
                        <div className="form-group">
                            <label htmlFor="auth-email">Adresse Email</label>
                            <div className="input-with-icon">
                                <Mail size={16} className="field-icon" />
                                <input
                                    id="auth-email"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="nom@rte-france.com"
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="auth-password">Mot de passe</label>
                            <div className="input-with-icon">
                                <Lock size={16} className="field-icon" />
                                <input
                                    id="auth-password"
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••••••"
                                    required
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="btn-auth-submit"
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? "Validation du JWT..." : "Se connecter"}
                        </button>
                    </form>
                ) : (
                    /* 2. Formulaire d'Inscription */
                    <form onSubmit={handleRegisterSubmit} className="auth-form">
                        <div className="form-group">
                            <label htmlFor="reg-fullname">Nom & Prénom</label>
                            <div className="input-with-icon">
                                <User size={16} className="field-icon" />
                                <input
                                    id="reg-fullname"
                                    type="text"
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                    placeholder="Jean Dupont"
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="reg-email">Adresse Email professionnelle</label>
                            <div className="input-with-icon">
                                <Mail size={16} className="field-icon" />
                                <input
                                    id="reg-email"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="jean.dupont@rte-france.com"
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="reg-password">Mot de passe sécurisé</label>
                            <div className="input-with-icon">
                                <Lock size={16} className="field-icon" />
                                <input
                                    id="reg-password"
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••••••"
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="reg-role">Rôle souhaité</label>
                            <select
                                id="reg-role"
                                className="auth-role-select"
                                value={requestedRole}
                                onChange={(e) => setRequestedRole(e.target.value as UserRole)}
                            >
                                <option value="viewer">Consultant Énergie (Lecture seule)</option>
                                <option value="analyst">Analyste Data (Exports & Modèles IA)</option>
                            </select>
                        </div>

                        <div className="reg-info-box">
                            <Clock size={15} />
                            <span>Votre compte sera placé en statut <strong>en attente d'approbation</strong> jusqu'à activation par un administrateur.</span>
                        </div>

                        <button
                            type="submit"
                            className="btn-auth-submit"
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? "Création du compte..." : "Créer le compte"}
                        </button>
                    </form>
                )}

                {/* Sélecteur de comptes de démonstration pour test immédiat */}
                {mode === "login" && (
                    <div className="quick-login-section">
                        <div className="quick-login-divider">
                            <span>OU TESTER UN RÔLE EN 1 CLIC</span>
                        </div>
                        <div className="quick-login-grid">
                            <button
                                type="button"
                                className="quick-role-btn btn-role-admin"
                                onClick={() => handleQuickLogin("admin@rte.fr", "RteAdmin2026!")}
                            >
                                <Shield size={16} className="text-admin" />
                                <div>
                                    <span className="quick-role-title">Administrateur</span>
                                    <span className="quick-role-desc">Validation comptes & MLOps</span>
                                </div>
                            </button>

                            <button
                                type="button"
                                className="quick-role-btn btn-role-analyst"
                                onClick={() => handleQuickLogin("analyst@rte.fr", "RteAnalyst2026!")}
                            >
                                <BarChart3 size={16} className="text-analyst" />
                                <div>
                                    <span className="quick-role-title">Analyste</span>
                                    <span className="quick-role-desc">Exports CSV & Benchmarks</span>
                                </div>
                            </button>

                            <button
                                type="button"
                                className="quick-role-btn btn-role-viewer"
                                onClick={() => handleQuickLogin("viewer@rte.fr", "RteViewer2026!")}
                            >
                                <Eye size={16} className="text-viewer" />
                                <div>
                                    <span className="quick-role-title">Consultant</span>
                                    <span className="quick-role-desc">Lecture seule</span>
                                </div>
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

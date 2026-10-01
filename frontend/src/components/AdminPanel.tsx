import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { getAuthHeaders, updateUserStatusApi, triggerPipelineApi, downloadMetricsCsv } from "../services/auth";
import { API_BASE_URL } from "../config";
import { Shield, Play, Users, FileDown, Lock, CheckCircle, AlertTriangle, CloudSun, Zap, Database, Download, Check, XCircle, Loader2, Sparkles, CheckCircle2 } from "lucide-react";
import { RoleBadge } from "./RoleBadge";

interface AdminPanelProps {
    onPipelineSuccess?: () => void;
}

interface PipelineProgressState {
    isRunning: boolean;
    pipelineType: string;
    stageIndex: number; // 0: RTE, 1: Météo, 2: dbt, 3: IA
    percent: number;
    elapsedSeconds: number;
    statusText: string;
    completed: boolean;
}

export const AdminPanel: React.FC<AdminPanelProps> = ({ onPipelineSuccess }) => {
    const { user, hasRole } = useAuth();
    const [usersList, setUsersList] = useState<any[] | null>(null);
    const [pipelineResult, setPipelineResult] = useState<{ message: string; type: string } | null>(null);
    const [exportResult, setExportResult] = useState<any | null>(null);
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const [actionError, setActionError] = useState<string | null>(null);
    const [actionSuccess, setActionSuccess] = useState<string | null>(null);

    // État de la barre de progression pour le Pipeline E2E
    const [pipelineProgress, setPipelineProgress] = useState<PipelineProgressState>({
        isRunning: false,
        pipelineType: "",
        stageIndex: 0,
        percent: 0,
        elapsedSeconds: 0,
        statusText: "",
        completed: false
    });

    const progressTimerRef = useRef<any>(null);

    const isAdmin = hasRole(["admin"]);
    const isAnalystOrAdmin = hasRole(["admin", "analyst"]);

    const pipelineStages = [
        { label: "1. Ingestion éCO2mix (RTE)", icon: Zap, detail: "Récupération des séries réelles quart-horaires" },
        { label: "2. Ingestion Météo (Open-Meteo)", icon: CloudSun, detail: "Relevés de température & vent à 10m" },
        { label: "3. Transformations dbt", icon: Database, detail: "Génération des tables fct_national_consumption & features" },
        { label: "4. Inférence IA (Chronos-Bolt)", icon: Sparkles, detail: "Prévisions TSFM & quantiles de confiance" }
    ];

    // Charger la liste des utilisateurs si admin connecté
    useEffect(() => {
        if (isAdmin) {
            handleFetchUsers();
        }
    }, [isAdmin]);

    // Nettoyer les timers au démontage
    useEffect(() => {
        return () => {
            if (progressTimerRef.current) {
                clearInterval(progressTimerRef.current);
            }
        };
    }, []);

    // Appel route réservée ADMIN : GET /api/admin/users
    const handleFetchUsers = async () => {
        setActionLoading("users");
        setActionError(null);
        try {
            const res = await fetch(`${API_BASE_URL}/api/admin/users`, {
                headers: getAuthHeaders()
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || `Erreur ${res.status}`);
            }
            const data = await res.json();
            setUsersList(data.users || []);
        } catch (err: any) {
            setActionError(err.message);
        } finally {
            setActionLoading(null);
        }
    };

    // [ADMIN] Validation / Activation / Désactivation d'un compte
    const handleToggleUserStatus = async (targetUser: any) => {
        const newStatus = !targetUser.is_active;
        setActionLoading(`user-toggle-${targetUser.id}`);
        setActionError(null);
        setActionSuccess(null);
        try {
            await updateUserStatusApi(targetUser.id, newStatus);
            setActionSuccess(`Le compte de ${targetUser.email} est désormais ${newStatus ? "ACTIVÉ / VALIDÉ" : "DÉSACTIVÉ"}.`);
            await handleFetchUsers();
        } catch (err: any) {
            setActionError(err.message);
        } finally {
            setActionLoading(null);
        }
    };

    // [ADMIN] Déclenchement d'un pipeline avec barre de progression interactive
    const handleTriggerPipeline = async (type: string) => {
        setActionLoading(`pipeline-${type}`);
        setActionError(null);
        setActionSuccess(null);
        setPipelineResult(null);

        // Si pipeline complet, initialiser la barre de progression
        if (type === "full_pipeline") {
            setPipelineProgress({
                isRunning: true,
                pipelineType: type,
                stageIndex: 0,
                percent: 10,
                elapsedSeconds: 0,
                statusText: "Initialisation et lancement du pipeline...",
                completed: false
            });

            let elapsed = 0;
            if (progressTimerRef.current) clearInterval(progressTimerRef.current);

            progressTimerRef.current = setInterval(() => {
                elapsed += 1;
                setPipelineProgress(prev => {
                    let nextStage = prev.stageIndex;
                    let nextPercent = prev.percent;
                    let nextText = prev.statusText;

                    if (elapsed < 2) {
                        nextStage = 0;
                        nextPercent = Math.min(25, prev.percent + 6);
                        nextText = "Étape 1/4 : Téléchargement des flux éCO2mix RTE France...";
                    } else if (elapsed < 5) {
                        nextStage = 1;
                        nextPercent = Math.min(50, prev.percent + 6);
                        nextText = "Étape 2/4 : Téléchargement des relevés météo Open-Meteo...";
                    } else if (elapsed < 8) {
                        nextStage = 2;
                        nextPercent = Math.min(75, prev.percent + 5);
                        nextText = "Étape 3/4 : Exécution des modèles dbt (staging & marts)...";
                    } else {
                        nextStage = 3;
                        nextPercent = Math.min(92, prev.percent + 3);
                        nextText = "Étape 4/4 : Génération des prévisions IA Chronos-Bolt...";
                    }

                    return {
                        ...prev,
                        elapsedSeconds: elapsed,
                        stageIndex: nextStage,
                        percent: nextPercent,
                        statusText: nextText
                    };
                });
            }, 1000);
        }

        try {
            const data = await triggerPipelineApi(type);
            
            if (progressTimerRef.current) {
                clearInterval(progressTimerRef.current);
            }

            if (type === "full_pipeline") {
                setPipelineProgress(prev => ({
                    ...prev,
                    percent: 100,
                    stageIndex: 3,
                    statusText: "Pipeline E2E exécuté et finalisé avec succès !",
                    completed: true
                }));
            }

            setPipelineResult({ message: data.message, type });
            setActionSuccess(data.message);

            if (onPipelineSuccess) {
                onPipelineSuccess();
            }
        } catch (err: any) {
            if (progressTimerRef.current) clearInterval(progressTimerRef.current);
            setPipelineProgress(prev => ({ ...prev, isRunning: false, completed: false }));
            setActionError(err.message);
        } finally {
            setActionLoading(null);
        }
    };

    // [ANALYSTE & ADMIN] Consultation des métriques à l'écran
    const handleViewMetrics = async () => {
        setActionLoading("metrics-view");
        setActionError(null);
        try {
            const res = await fetch(`${API_BASE_URL}/api/analyst/export-metrics`, {
                headers: getAuthHeaders()
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || `Erreur ${res.status}`);
            }
            const data = await res.json();
            setExportResult(data);
        } catch (err: any) {
            setActionError(err.message);
        } finally {
            setActionLoading(null);
        }
    };

    // [ANALYSTE & ADMIN] Téléchargement réel du fichier CSV
    const handleDownloadCsv = async () => {
        setActionLoading("metrics-download");
        setActionError(null);
        try {
            await downloadMetricsCsv();
            setActionSuccess("Fichier CSV généré et téléchargé avec succès !");
        } catch (err: any) {
            setActionError(err.message);
        } finally {
            setActionLoading(null);
        }
    };

    if (!user) {
        return (
            <div className="rbac-notice-card">
                <div className="rbac-notice-icon">
                    <Lock size={24} />
                </div>
                <div>
                    <h4>Espace d'Administration & Métriques Réservées (RBAC)</h4>
                    <p>
                        Connectez-vous avec un compte <strong>Analyste</strong> ou <strong>Administrateur</strong> pour accéder aux actions MLOps, aux exports de métriques et à la gestion des utilisateurs.
                    </p>
                </div>
            </div>
        );
    }

    const pendingUsersCount = usersList ? usersList.filter(u => !u.is_active).length : 0;

    return (
        <div className="admin-panel-card">
            <div className="admin-panel-header">
                <div className="admin-panel-title">
                    <Shield size={20} className="text-admin" />
                    <h3>Contrôle d'Accès, MLOps & Téléchargements RBAC</h3>
                </div>
                <div className="admin-panel-user">
                    <span>Connecté : <strong>{user.email}</strong></span>
                    <RoleBadge role={user.role} />
                </div>
            </div>

            {/* Alertes d'état */}
            {actionError && (
                <div className="auth-alert alert-error" style={{ marginBottom: "1rem" }}>
                    <AlertTriangle size={16} />
                    <span>{actionError}</span>
                </div>
            )}

            {actionSuccess && (
                <div className="auth-alert alert-success" style={{ marginBottom: "1rem" }}>
                    <CheckCircle size={16} />
                    <span>{actionSuccess}</span>
                </div>
            )}

            {/* BARRE DE PROGRESSION EN DIRECT POUR LE PIPELINE E2E */}
            {pipelineProgress.isRunning && (
                <div className={`pipeline-progress-container ${pipelineProgress.completed ? "progress-completed" : ""}`}>
                    <div className="progress-header">
                        <div className="progress-title-row">
                            {pipelineProgress.completed ? (
                                <CheckCircle2 size={18} className="text-success" />
                            ) : (
                                <Loader2 size={18} className="spinning text-info" />
                            )}
                            <h4>
                                {pipelineProgress.completed
                                    ? "Pipeline Complet E2E terminé !"
                                    : `Exécution du Pipeline Complet E2E (${pipelineProgress.elapsedSeconds}s)`}
                            </h4>
                        </div>
                        <span className="progress-percent-badge">{pipelineProgress.percent}%</span>
                    </div>

                    {/* Barre visuelle */}
                    <div className="progress-track">
                        <div
                            className="progress-bar-fill"
                            style={{ width: `${pipelineProgress.percent}%` }}
                        ></div>
                    </div>

                    {/* Message d'état de l'étape courante */}
                    <p className="progress-status-text">{pipelineProgress.statusText}</p>

                    {/* Étapes séquentielles du pipeline */}
                    <div className="pipeline-steps-grid">
                        {pipelineStages.map((stg, idx) => {
                            const IconComponent = stg.icon;
                            const isPast = idx < pipelineProgress.stageIndex || pipelineProgress.completed;
                            const isCurrent = idx === pipelineProgress.stageIndex && !pipelineProgress.completed;

                            return (
                                <div
                                    key={idx}
                                    className={`pipeline-step-item ${isPast ? "step-done" : isCurrent ? "step-active" : "step-pending"}`}
                                >
                                    <div className="step-icon-wrapper">
                                        {isPast ? (
                                            <Check size={14} className="text-success" />
                                        ) : isCurrent ? (
                                            <Loader2 size={14} className="spinning text-info" />
                                        ) : (
                                            <IconComponent size={14} />
                                        )}
                                    </div>
                                    <div className="step-text-group">
                                        <span className="step-name">{stg.label}</span>
                                        <span className="step-detail">{stg.detail}</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            <div className="admin-actions-grid">
                {/* 1. Gestion des Utilisateurs et Approbation Admin */}
                <div className={`action-box ${isAdmin ? "action-box-active" : "action-box-locked"}`}>
                    <div className="action-box-header">
                        <div className="action-title-group">
                            <Users size={18} />
                            <h4>Validation & Utilisateurs</h4>
                        </div>
                        <span className="role-tag tag-admin">
                            {pendingUsersCount > 0 ? `${pendingUsersCount} en attente` : "Admin"}
                        </span>
                    </div>
                    <p className="action-desc">
                        Validez les nouveaux comptes en attente d'approbation et gérez les rôles.
                    </p>

                    <button
                        className="btn-action-trigger"
                        onClick={handleFetchUsers}
                        disabled={!isAdmin || actionLoading === "users"}
                    >
                        {actionLoading === "users" ? "Actualisation..." : "Rafraîchir la liste"}
                    </button>

                    {usersList && (
                        <div className="action-results-table">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Utilisateur</th>
                                        <th>Rôle</th>
                                        <th>Statut</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {usersList.map((u) => (
                                        <tr key={u.id} className={!u.is_active ? "row-pending-approval" : ""}>
                                            <td>
                                                <div className="user-table-cell">
                                                    <span className="user-email-text">{u.email}</span>
                                                    {u.full_name && <span className="user-name-sub">{u.full_name}</span>}
                                                </div>
                                            </td>
                                            <td><RoleBadge role={u.role} showIcon={false} /></td>
                                            <td>
                                                {u.is_active ? (
                                                    <span className="status-pill status-active">Actif</span>
                                                ) : (
                                                    <span className="status-pill status-pending">En attente</span>
                                                )}
                                            </td>
                                            <td>
                                                {isAdmin && (
                                                    <button
                                                        className={`btn-user-toggle ${u.is_active ? "btn-deactivate" : "btn-approve"}`}
                                                        onClick={() => handleToggleUserStatus(u)}
                                                        disabled={actionLoading === `user-toggle-${u.id}`}
                                                        title={u.is_active ? "Désactiver ce compte" : "Approuver et activer ce compte"}
                                                    >
                                                        {u.is_active ? (
                                                            <>
                                                                <XCircle size={12} />
                                                                <span>Désactiver</span>
                                                            </>
                                                        ) : (
                                                            <>
                                                                <Check size={12} />
                                                                <span>Approuver</span>
                                                            </>
                                                        )}
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                {/* 2. Déclenchement Pipelines MLOps & Ingestion (RTE, Weather, dbt, E2E) */}
                <div className={`action-box ${isAdmin ? "action-box-active" : "action-box-locked"}`}>
                    <div className="action-box-header">
                        <div className="action-title-group">
                            <Play size={18} />
                            <h4>Pipelines de Données & IA</h4>
                        </div>
                        <span className="role-tag tag-admin">Admin Seul</span>
                    </div>
                    <p className="action-desc">
                        Actualisez les données météo, l'ingestion RTE ou relancez le cycle complet dbt et inférence IA.
                    </p>

                    <div className="btn-pipeline-grid">
                        <button
                            className="btn-pipeline-action"
                            onClick={() => handleTriggerPipeline("ingestion_weather")}
                            disabled={!isAdmin || actionLoading === "pipeline-ingestion_weather"}
                        >
                            <CloudSun size={15} className="text-warning" />
                            <span>1. Ingestion Météo (Open-Meteo)</span>
                        </button>

                        <button
                            className="btn-pipeline-action"
                            onClick={() => handleTriggerPipeline("ingestion_rte")}
                            disabled={!isAdmin || actionLoading === "pipeline-ingestion_rte"}
                        >
                            <Zap size={15} className="text-warning" />
                            <span>2. Ingestion RTE (éCO2mix)</span>
                        </button>

                        <button
                            className="btn-pipeline-action"
                            onClick={() => handleTriggerPipeline("dbt_run")}
                            disabled={!isAdmin || actionLoading === "pipeline-dbt_run"}
                        >
                            <Database size={15} className="text-info" />
                            <span>3. Transformations dbt</span>
                        </button>

                        <button
                            className="btn-pipeline-action btn-pipeline-e2e"
                            onClick={() => handleTriggerPipeline("full_pipeline")}
                            disabled={!isAdmin || actionLoading === "pipeline-full_pipeline"}
                        >
                            <Play size={15} />
                            <span>4. Pipeline Complet E2E (IA)</span>
                        </button>
                    </div>

                    {pipelineResult && !pipelineProgress.isRunning && (
                        <div className="action-result-box">
                            <CheckCircle size={16} className="text-success" />
                            <span>{pipelineResult.message}</span>
                        </div>
                    )}
                </div>

                {/* 3. Export des Métriques & Téléchargement CSV */}
                <div className={`action-box ${isAnalystOrAdmin ? "action-box-active" : "action-box-locked"}`}>
                    <div className="action-box-header">
                        <div className="action-title-group">
                            <FileDown size={18} />
                            <h4>Export des Métriques & Fichier CSV</h4>
                        </div>
                        <span className="role-tag tag-analyst">Analyste & Admin</span>
                    </div>
                    <p className="action-desc">
                        Consultez les scores des modèles ou téléchargez les prévisions quart-horaires et erreurs au format CSV.
                    </p>

                    <div className="btn-group-actions">
                        <button
                            className="btn-action-trigger"
                            onClick={handleViewMetrics}
                            disabled={!isAnalystOrAdmin || actionLoading === "metrics-view"}
                        >
                            {actionLoading === "metrics-view" ? "Chargement..." : "Afficher les Métriques"}
                        </button>

                        <button
                            className="btn-action-trigger btn-download-csv"
                            onClick={handleDownloadCsv}
                            disabled={!isAnalystOrAdmin || actionLoading === "metrics-download"}
                        >
                            <Download size={14} />
                            <span>{actionLoading === "metrics-download" ? "Génération..." : "Télécharger CSV"}</span>
                        </button>
                    </div>

                    {exportResult && (
                        <div className="action-json-box">
                            <pre>{JSON.stringify(exportResult, null, 2)}</pre>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

import React from "react";
import type { UserRole } from "../types/auth";
import { Shield, BarChart3, Eye } from "lucide-react";

interface RoleBadgeProps {
    role: UserRole;
    showIcon?: boolean;
}

export const RoleBadge: React.FC<RoleBadgeProps> = ({ role, showIcon = true }) => {
    switch (role) {
        case "admin":
            return (
                <span className="role-badge badge-admin">
                    {showIcon && <Shield size={13} className="role-icon" />}
                    Administrateur
                </span>
            );
        case "analyst":
            return (
                <span className="role-badge badge-analyst">
                    {showIcon && <BarChart3 size={13} className="role-icon" />}
                    Analyste Data
                </span>
            );
        case "viewer":
        default:
            return (
                <span className="role-badge badge-viewer">
                    {showIcon && <Eye size={13} className="role-icon" />}
                    Consultant
                </span>
            );
    }
};

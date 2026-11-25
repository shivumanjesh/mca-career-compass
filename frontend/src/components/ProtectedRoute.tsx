import React from "react";
import { Navigate, Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "../app/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: string;
  requiredAnyPermissions?: string[];
  loginPath?: "/login" | "/admin/login";
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredPermission,
  requiredAnyPermissions,
  loginPath = "/login",
}) => {
  const { auth, loading, hasPermission } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-sm font-medium text-slate-600">Verifying session...</div>
      </div>
    );
  }

  if (!auth) {
    return <Navigate to={loginPath} replace />;
  }

  const missingSingle = Boolean(requiredPermission && !hasPermission(requiredPermission));
  const missingAny = Boolean(
    requiredAnyPermissions &&
      requiredAnyPermissions.length > 0 &&
      !requiredAnyPermissions.some((p) => hasPermission(p)),
  );

  if (missingSingle || missingAny) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white rounded-xl border border-slate-200 shadow-sm p-8 text-center space-y-4">
          <div className="mx-auto h-12 w-12 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h1 className="text-lg font-bold text-[#0F2942]">Access Denied</h1>
          <p className="text-sm text-slate-600">
            Your active role does not have permission to view this page.
          </p>
          <Link
            to="/dashboard"
            className="inline-flex items-center justify-center rounded-md bg-[#0F2942] px-4 py-2 text-sm font-medium text-white hover:bg-[#1E3A5F]"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};


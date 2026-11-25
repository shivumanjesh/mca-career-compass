import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  ensureCsrfCookie,
  fetchAuthMe,
  loginPortal,
  logoutSession,
  switchInstitution as switchInstitutionApi,
} from "../services/authService";
import type { AuthMeResponse, LoginPayload, RoleCode } from "../types/auth";

interface AuthContextValue {
  auth: AuthMeResponse | null;
  loading: boolean;
  refreshAuth: () => Promise<void>;
  login: (payload: LoginPayload) => Promise<AuthMeResponse>;
  logout: () => Promise<void>;
  switchInstitution: (institutionId: string) => Promise<AuthMeResponse>;
  hasPermission: (permissionCode: string) => boolean;
  hasRole: (roleCode: RoleCode) => boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [auth, setAuth] = useState<AuthMeResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshAuth = useCallback(async () => {
    try {
      const me = await fetchAuthMe();
      setAuth(me);
    } catch {
      setAuth(null);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        await ensureCsrfCookie();
        const me = await fetchAuthMe();
        if (mounted) setAuth(me);
      } catch {
        if (mounted) setAuth(null);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const me = await loginPortal(payload);
    setAuth(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutSession();
    } finally {
      setAuth(null);
    }
  }, []);

  const switchInstitution = useCallback(async (institutionId: string) => {
    const me = await switchInstitutionApi(institutionId);
    setAuth(me);
    return me;
  }, []);

  const hasPermission = useCallback(
    (permissionCode: string) => Boolean(auth?.permissions.includes(permissionCode)),
    [auth],
  );

  const hasRole = useCallback(
    (roleCode: RoleCode) =>
      Boolean(auth?.platform_roles.includes(roleCode) || auth?.active_roles.includes(roleCode)),
    [auth],
  );

  return (
    <AuthContext.Provider
      value={{
        auth,
        loading,
        refreshAuth,
        login,
        logout,
        switchInstitution,
        hasPermission,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return ctx;
}


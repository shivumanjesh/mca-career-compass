import { apiClient } from "./apiClient";
import type { AuthMeResponse, LoginPayload } from "../types/auth";

export async function ensureCsrfCookie(): Promise<void> {
  await apiClient.get("/auth/csrf/");
}

export async function fetchAuthMe(): Promise<AuthMeResponse> {
  const response = await apiClient.get<AuthMeResponse>("/auth/me/");
  return response.data;
}

export async function loginPortal(payload: LoginPayload): Promise<AuthMeResponse> {
  await ensureCsrfCookie();
  const response = await apiClient.post<AuthMeResponse>("/auth/login/", payload);
  return response.data;
}

export async function logoutSession(): Promise<void> {
  await ensureCsrfCookie();
  await apiClient.post("/auth/logout/");
}

export async function switchInstitution(institutionId: string): Promise<AuthMeResponse> {
  await ensureCsrfCookie();
  const response = await apiClient.post<AuthMeResponse>("/auth/switch-institution/", {
    institution_id: institutionId,
  });
  return response.data;
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await ensureCsrfCookie();
  await apiClient.post("/auth/change-password/", {
    old_password: oldPassword,
    new_password: newPassword,
  });
}

export async function requestPasswordReset(email: string): Promise<string> {
  await ensureCsrfCookie();
  const response = await apiClient.post<{ detail: string }>("/auth/password-reset/request/", {
    email,
  });
  return response.data.detail;
}

export async function confirmPasswordReset(
  uid: string,
  token: string,
  newPassword: string,
): Promise<string> {
  await ensureCsrfCookie();
  const response = await apiClient.post<{ detail: string }>("/auth/password-reset/confirm/", {
    uid,
    token,
    new_password: newPassword,
  });
  return response.data.detail;
}


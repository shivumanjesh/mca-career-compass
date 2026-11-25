import axios, { AxiosError } from "axios";
import type { ApiErrorPayload } from "../types/api";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  headers: {
    "Content-Type": "application/json",
  },
});

export function parseApiError(error: unknown): ApiErrorPayload {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<Partial<ApiErrorPayload>>;
    const data = axiosError.response?.data;
    if (data && typeof data === "object" && typeof data.message === "string") {
      return {
        code: typeof data.code === "string" ? data.code : "api_error",
        message: data.message,
        details: data.details,
      };
    }
    if (!axiosError.response) {
      return {
        code: "network_error",
        message: "Unable to reach the backend API server. Verify it is running on port 8000.",
      };
    }
    return {
      code: `http_${axiosError.response.status}`,
      message: `Request failed with status ${axiosError.response.status}.`,
    };
  }
  return {
    code: "unexpected_error",
    message: error instanceof Error ? error.message : "An unexpected error occurred.",
  };
}


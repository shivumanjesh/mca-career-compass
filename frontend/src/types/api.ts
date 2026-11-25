export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: unknown;
}

export interface HealthCheckResponse {
  status: "ok" | "degraded";
  service: string;
  database: "connected" | "unavailable";
  timestamp: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}


import { apiClient } from "./apiClient";
import type { PaginatedResponse } from "../types/api";
import type { AuditEventRecord } from "../types/audit";

export async function listAuditEvents(params: {
  page?: number;
  search?: string;
  action?: string;
  entity_type?: string;
}): Promise<PaginatedResponse<AuditEventRecord>> {
  const res = await apiClient.get<PaginatedResponse<AuditEventRecord>>("/audit-events/", {
    params,
  });
  return res.data;
}


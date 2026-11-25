export interface AuditEventRecord {
  id: string;
  institution_id: string | null;
  institution_code: string | null;
  actor_user_id: string | null;
  actor_email: string | null;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before_json: Record<string, unknown> | null;
  after_json: Record<string, unknown> | null;
  ip_hash: string;
  created_at: string;
}


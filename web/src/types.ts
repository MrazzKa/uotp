export type RoleCode = "ADMIN" | "DISPATCHER" | "EXECUTOR" | "AKIM" | "INSPECTOR";

export type User = {
  id: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  language: string;
  role: { id: string; code: RoleCode; name_ru: string; name_kk: string; permissions: Record<string, unknown> };
  tenant: { id: string; code: string; name_ru: string; name_kk: string; timezone: string; locale_default: string };
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type CatalogItem = {
  id: string;
  code?: string;
  name_ru: string;
  name_kk: string;
  parent_id?: string | null;
  default_priority?: string;
  default_department_id?: string | null;
  icon?: string | null;
  color?: string | null;
  type?: string;
};

export type IssueStatus =
  | "NEW"
  | "QUALIFICATION"
  | "ASSIGNED"
  | "ACCEPTED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "INSPECTION"
  | "CLOSED"
  | "REJECTED"
  | "RETURNED"
  | "DUPLICATE";

export type Issue = {
  id: string;
  public_number: string;
  title: string;
  description?: string;
  source: string;
  status: IssueStatus;
  priority: string;
  category: CatalogItem | null;
  district: CatalogItem | null;
  department: CatalogItem | null;
  assigned_to: { id: string; full_name: string; email: string | null } | null;
  created_by?: { id: string; full_name: string; email: string | null };
  created_at: string;
  accepted_at?: string | null;
  on_site_at?: string | null;
  completed_at?: string | null;
  closed_at?: string | null;
  reaction_due_at: string | null;
  sla_due_at: string | null;
  inspection_due_at: string | null;
  is_overdue: boolean;
  sla_paused_at: string | null;
  address?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  attachments?: Array<{
    id: string;
    file_url: string;
    medium_url: string | null;
    thumbnail_url: string | null;
    attachment_type: string;
    mime_type: string;
  }>;
  comments?: Array<{
    id: string;
    content: string;
    is_internal: boolean;
    created_at: string;
    author: { full_name: string };
  }>;
  history?: Array<{
    id: string;
    action: string;
    from_status: string | null;
    to_status: string | null;
    created_at: string;
    actor: { full_name: string } | null;
  }>;
};

export type IssueListResponse = {
  items: Issue[];
  next_cursor: string | null;
};

export type DashboardSummary = {
  counts: {
    in_progress: number;
    overdue: number;
    inspection: number;
    closed_today: number;
    new: number;
  };
  sla_on_time_pct: number;
  per_day: Array<{ date: string; count: number }>;
  by_status: Array<{ status: IssueStatus | string; count: number }>;
  hot_zones: Array<{ district_id: string | null; name: string; count: number }>;
  recent_events: Array<{
    issue_id: string;
    public_number: string;
    action: string;
    to_status: IssueStatus | string | null;
    created_at: string;
  }>;
};

export type NotificationItem = {
  id: string;
  type: string;
  title: string;
  body: string;
  issue_id: string | null;
  is_read: boolean;
  created_at: string;
};

export type NotificationListResponse = {
  items: NotificationItem[];
  next_cursor: string | null;
};

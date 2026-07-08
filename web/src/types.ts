export type RoleCode =
  | "ADMIN"
  | "AKIM"
  | "DEPUTY"
  | "APPARAT"
  | "DEPT_HEAD"
  | "AKIM_SO"
  | "SPECIALIST"
  | "OPERATOR"
  | "CONTRACTOR";

export type UserMini = { id: string; full_name: string; email: string | null };

export type Role = { id: string; code: string; name_ru: string; name_kk: string };

export type User = {
  id: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  language: string;
  position_title?: string | null;
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
  icon?: string | null;
  color?: string | null;
  type?: string;
};

export type IssueStatus =
  | "DRAFT"
  | "NEW"
  | "ASSIGNED"
  | "REVIEW_CONTROLLER"
  | "REVIEW_AUTHOR"
  | "CLOSED"
  | "ON_HOLD";

export type Issue = {
  id: string;
  public_number: string;
  title: string;
  description?: string;
  source: string;
  task_type: string;
  status: IssueStatus;
  priority: string;
  importance: string;
  category: CatalogItem | null;
  sphere: CatalogItem | null;
  district: CatalogItem | null;
  assigned_to: UserMini | null;
  controller: UserMini | null;
  created_by?: UserMini;
  created_at: string;
  due_at: string | null;
  closed_at?: string | null;
  is_overdue: boolean;
  on_personal_control?: boolean;
  reopen_count?: number;
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
    on_review: number;
    closed_today: number;
    new: number;
  };
  sla_on_time_pct: number;
  per_day: Array<{ date: string; count: number }>;
  by_status: Array<{ status: IssueStatus | string; count: number }>;
  hot_zones: Array<{ district_id: string | null; name: string; count: number }>;
  okrug_monitoring: Array<{ id: string | null; name: string; total: number; done: number; pct: number }>;
  recent_events: Array<{
    issue_id: string;
    public_number: string;
    action: string;
    to_status: IssueStatus | string | null;
    created_at: string;
  }>;
};

export type OkrugBreakdown = { name: string; total: number; done: number; pct: number };
export type OkrugDetail = { name: string; by_user: OkrugBreakdown[]; by_sphere: OkrugBreakdown[] };

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

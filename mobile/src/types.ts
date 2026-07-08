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

export type IssueStatus =
  | "DRAFT"
  | "NEW"
  | "ASSIGNED"
  | "REVIEW_CONTROLLER"
  | "REVIEW_AUTHOR"
  | "CLOSED"
  | "ON_HOLD";

export type UserMini = { id: string; full_name: string; organization?: string | null };

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
  icon?: string | null;
  color?: string | null;
  default_priority?: string | null;
};

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
  address?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  attachments?: Array<{
    id: string;
    file_url: string;
    thumbnail_url: string | null;
    medium_url: string | null;
  }>;
  history?: Array<{
    id: string;
    action: string;
    from_status: string | null;
    to_status: string | null;
    created_at: string;
    actor: { full_name: string } | null;
  }>;
  comments?: Array<{
    id: string;
    content: string;
    created_at: string;
    author: { full_name: string };
  }>;
};

export type IssueListResponse = {
  items: Issue[];
  next_cursor: string | null;
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

export type VoiceDraft = {
  transcript: string;
  title: string;
  importance: string;
  sphere_id: string | null;
  sphere_name: string | null;
  executor_id: string | null;
  executor_name: string | null;
  due_at: string | null;
};

export type DashboardSummary = {
  counts: { in_progress: number; overdue: number; on_review: number; closed_today: number; new: number };
  okrug_monitoring: Array<{ name: string; total: number; done: number; pct: number }>;
};

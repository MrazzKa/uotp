export type RoleCode = "ADMIN" | "DISPATCHER" | "EXECUTOR" | "AKIM" | "INSPECTOR";

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
  default_priority?: string | null;
};

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
  assigned_to: { id: string; full_name: string } | null;
  created_at: string;
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

import type { IssueStatus } from "../types";

export const chartPalette = ["#2563EB", "#7C3AED", "#14B8A6", "#F59E0B", "#94A3B8"];

// Единый источник группировки статус -> цвет (используется бейджем и картой).
const ACTIVE_STATUSES = ["NEW", "ASSIGNED"];
const REVIEW_STATUSES = ["REVIEW_CONTROLLER", "REVIEW_AUTHOR"];

const statusHexPalette = {
  overdue: "#EF4444",
  active: "#2563EB",
  review: "#F59E0B",
  closed: "#10B981",
  muted: "#94A3B8"
};

export function statusHex(status: IssueStatus | string, isOverdue = false): string {
  if (isOverdue) return statusHexPalette.overdue;
  if (ACTIVE_STATUSES.includes(status)) return statusHexPalette.active;
  if (REVIEW_STATUSES.includes(status)) return statusHexPalette.review;
  if (status === "CLOSED") return statusHexPalette.closed;
  return statusHexPalette.muted;
}

/** i18n key for a localized status label, e.g. statusLabelKey("NEW") -> "st_NEW". */
export function statusLabelKey(status: IssueStatus | string): string {
  return `st_${status}`;
}

export function statusColor(status: IssueStatus | string, isOverdue = false) {
  if (isOverdue) {
    return {
      bg: "bg-red-50 dark:bg-red-950/40",
      text: "text-red-700 dark:text-red-200",
      dot: "bg-danger"
    };
  }
  if (ACTIVE_STATUSES.includes(status)) {
    return {
      bg: "bg-blue-50 dark:bg-blue-950/35",
      text: "text-blue-700 dark:text-blue-200",
      dot: "bg-info"
    };
  }
  if (REVIEW_STATUSES.includes(status)) {
    return {
      bg: "bg-amber-50 dark:bg-amber-950/35",
      text: "text-amber-700 dark:text-amber-200",
      dot: "bg-warning"
    };
  }
  if (status === "CLOSED") {
    return {
      bg: "bg-emerald-50 dark:bg-emerald-950/35",
      text: "text-emerald-700 dark:text-emerald-200",
      dot: "bg-success"
    };
  }
  return {
    bg: "bg-slate-100 dark:bg-slate-800",
    text: "text-slate-600 dark:text-slate-300",
    dot: "bg-slate-400"
  };
}

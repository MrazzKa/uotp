export const palettes = {
  light: {
    background: "#F8FAFC",
    surface: "#FFFFFF",
    surface2: "#F5F7FA",
    border: "#E5E7EB",
    text: "#111827",
    mutedText: "#6B7280",
    primary: "#2563EB",
    primaryHover: "#1D4ED8",
    primarySoft: "#EFF4FF",
    success: "#22C55E",
    warning: "#F59E0B",
    danger: "#EF4444",
    info: "#2563EB"
  },
  dark: {
    background: "#0B1220",
    surface: "#0F172A",
    surface2: "#1E293B",
    border: "#334155",
    text: "#F1F5F9",
    mutedText: "#94A3B8",
    primary: "#3B82F6",
    primaryHover: "#60A5FA",
    primarySoft: "#16233D",
    success: "#34D399",
    warning: "#FBBF24",
    danger: "#F87171",
    info: "#3B82F6"
  }
};

export const radii = {
  card: 16,
  control: 12,
  chip: 999
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32
};

export type ThemeName = keyof typeof palettes;
export type ThemeColors = typeof palettes.light;

export function statusColor(status: string, isOverdue = false, colors: ThemeColors = palettes.light) {
  if (isOverdue) return { bg: colors.danger, soft: colors.danger, text: "#FFFFFF" };
  if (["QUALIFICATION", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"].includes(status)) {
    return { bg: colors.info, soft: colors.primarySoft, text: colors.primary };
  }
  if (["COMPLETED", "INSPECTION", "RETURNED"].includes(status)) {
    return { bg: colors.warning, soft: colors.surface2, text: colors.warning };
  }
  if (status === "CLOSED") return { bg: colors.success, soft: colors.surface2, text: colors.success };
  if (status === "REJECTED" || status === "DUPLICATE") {
    return { bg: colors.mutedText, soft: colors.surface2, text: colors.mutedText };
  }
  return { bg: colors.info, soft: colors.primarySoft, text: colors.text };
}

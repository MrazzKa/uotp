import axios from "axios";

import { useAuthStore } from "../store/auth";
import type {
  CatalogItem,
  DashboardSummary,
  Issue,
  IssueListResponse,
  NotificationListResponse,
  OkrugDetail,
  Role,
  TokenPair,
  User
} from "../types";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// De-duplicate concurrent refreshes: many 401s should trigger a single refresh.
let refreshPromise: Promise<TokenPair> | null = null;

function refreshTokens(refreshToken: string): Promise<TokenPair> {
  if (!refreshPromise) {
    refreshPromise = axios
      .post<TokenPair>(`${api.defaults.baseURL}/auth/refresh`, { refresh_token: refreshToken })
      .then((response) => response.data)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const store = useAuthStore.getState();
    if (error.response?.status === 401 && store.refreshToken && !error.config._retry) {
      error.config._retry = true;
      try {
        const data = await refreshTokens(store.refreshToken);
        store.setTokens(data);
        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return api.request(error.config);
      } catch (refreshError) {
        // Refresh failed (token expired/revoked): drop the session.
        store.logout();
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export async function login(loginValue: string, password: string, totpCode?: string) {
  const { data } = await api.post<TokenPair>("/auth/login", {
    login: loginValue,
    password,
    totp_code: totpCode
  });
  useAuthStore.getState().setTokens(data);
  return data;
}

export async function logout() {
  const store = useAuthStore.getState();
  const refreshToken = store.refreshToken;
  try {
    if (refreshToken) {
      await api.post("/auth/logout", { refresh_token: refreshToken });
    }
  } catch {
    // Best-effort server-side revocation; always clear local state.
  } finally {
    store.logout();
  }
}

export async function fetchMe() {
  const { data } = await api.get<User>("/auth/me");
  useAuthStore.getState().setUser(data);
  return data;
}

export async function changePassword(currentPassword: string, newPassword: string) {
  await api.post("/auth/change-password", { current_password: currentPassword, new_password: newPassword });
}

export async function fetchCatalogs() {
  const [categories, departments, districts, spheres, users] = await Promise.all([
    api.get<CatalogItem[]>("/categories"),
    api.get<CatalogItem[]>("/departments"),
    api.get<CatalogItem[]>("/districts"),
    api.get<CatalogItem[]>("/spheres"),
    api.get<User[]>("/users")
  ]);
  return {
    categories: categories.data,
    departments: departments.data,
    districts: districts.data,
    spheres: spheres.data,
    users: users.data
  };
}

export async function fetchDashboardSummary() {
  const { data } = await api.get<DashboardSummary>("/dashboard/summary");
  return data;
}

export async function fetchRoles() {
  const { data } = await api.get<Role[]>("/roles");
  return data;
}

export async function fetchOkrugDetail(id: string) {
  const { data } = await api.get<OkrugDetail>(`/dashboard/okrug/${id}`);
  return data;
}

export async function createSphere(payload: Record<string, unknown>) {
  const { data } = await api.post<CatalogItem>("/spheres", payload);
  return data;
}

export async function updateSphere(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<CatalogItem>(`/spheres/${id}`, payload);
  return data;
}

export async function deleteSphere(id: string) {
  await api.delete(`/spheres/${id}`);
}

export async function createDepartment(payload: Record<string, unknown>) {
  const { data } = await api.post<CatalogItem>("/departments", payload);
  return data;
}

export async function deleteDepartment(id: string) {
  await api.delete(`/departments/${id}`);
}

export async function createUser(payload: Record<string, unknown>) {
  const { data } = await api.post<User>("/users", payload);
  return data;
}

export async function updateUser(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<User>(`/users/${id}`, payload);
  return data;
}

export async function fetchNotifications(params: { is_read?: boolean; cursor?: string; limit?: number } = {}) {
  const { data } = await api.get<NotificationListResponse>("/notifications", { params });
  return data;
}

export async function fetchUnreadCount() {
  const { data } = await api.get<{ count: number }>("/notifications/unread-count");
  return data.count;
}

export async function markNotificationRead(id: string) {
  const { data } = await api.post(`/notifications/${id}/read`);
  return data;
}

export async function markAllNotificationsRead() {
  const { data } = await api.post<{ count: number }>("/notifications/read-all");
  return data.count;
}

export async function fetchIssues(params: Record<string, string | undefined>) {
  const { data } = await api.get<IssueListResponse>("/issues", { params });
  return data;
}

export async function fetchIssue(id: string) {
  const { data } = await api.get<Issue>(`/issues/${id}`);
  return data;
}

export async function createIssue(payload: Record<string, unknown>) {
  const { data } = await api.post<Issue>("/issues", payload);
  return data;
}

export async function submitIssue(id: string, report?: string) {
  const { data } = await api.post<Issue>(`/issues/${id}/submit`, { report });
  return data;
}

export async function updateIssue(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<Issue>(`/issues/${id}`, payload);
  return data;
}

export async function setPersonalControl(id: string, on: boolean, importance = "NORMAL") {
  const { data } = await api.post<Issue>(`/issues/${id}/personal-control`, { on, importance });
  return data;
}

export async function assignIssue(id: string, payload: Record<string, unknown>) {
  const { data } = await api.post<Issue>(`/issues/${id}/assign`, payload);
  return data;
}

export async function transitionIssue(id: string, status: string, payload: Record<string, unknown> = {}) {
  const { data } = await api.post<Issue>(`/issues/${id}/transition`, { status, payload });
  return data;
}

export async function addIssueComment(id: string, content: string) {
  const { data } = await api.post(`/issues/${id}/comments`, { content, language: "ru" });
  return data;
}

export type MapCluster = {
  longitude: number;
  latitude: number;
  count: number;
  dominant_status: string;
};

export type HeatmapPoint = {
  longitude: number;
  latitude: number;
  weight: number;
};

export async function fetchMapIssues(params: Record<string, string | undefined>) {
  const { data } = await api.get<GeoJSON.FeatureCollection>("/map/issues", { params });
  return data;
}

export async function fetchMapClusters(params: Record<string, string | undefined>) {
  const { data } = await api.get<MapCluster[]>("/map/clusters", { params });
  return data;
}

export async function fetchMapHeatmap(params: Record<string, string | undefined>) {
  const { data } = await api.get<HeatmapPoint[]>("/map/heatmap", { params });
  return data;
}

export async function fetchMapDistricts() {
  const { data } = await api.get<GeoJSON.FeatureCollection>("/map/districts");
  return data;
}

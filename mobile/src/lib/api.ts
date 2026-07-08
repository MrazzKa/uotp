import Constants from "expo-constants";
import axios from "axios";

import { useAuthStore } from "../store/auth";
import type { CatalogItem, DashboardSummary, Issue, IssueListResponse, NotificationListResponse, TokenPair, User, VoiceDraft } from "../types";

const apiUrl = (Constants.expoConfig?.extra?.apiUrl as string | undefined) ?? "http://localhost:8000/api/v1";

export const api = axios.create({ baseURL: apiUrl });

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const store = useAuthStore.getState();
    if (error.response?.status === 401 && store.refreshToken && !error.config._retry) {
      error.config._retry = true;
      const { data } = await axios.post<TokenPair>(`${api.defaults.baseURL}/auth/refresh`, {
        refresh_token: store.refreshToken
      });
      await store.setTokens(data);
      error.config.headers.Authorization = `Bearer ${data.access_token}`;
      return api.request(error.config);
    }
    return Promise.reject(error);
  }
);

export async function login(loginValue: string, password: string) {
  const { data } = await api.post<TokenPair>("/auth/login", { login: loginValue, password });
  await useAuthStore.getState().setTokens(data);
}

export async function fetchMe() {
  const { data } = await api.get<User>("/auth/me");
  useAuthStore.getState().setUser(data);
  return data;
}

export async function changePassword(currentPassword: string, newPassword: string) {
  await api.post("/auth/change-password", { current_password: currentPassword, new_password: newPassword });
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
    await store.logout();
  }
}

export async function fetchCatalogs() {
  const { data } = await api.get<CatalogItem[]>("/categories");
  return data;
}

export async function fetchSpheres() {
  const { data } = await api.get<CatalogItem[]>("/spheres");
  return data;
}

export async function fetchUsers() {
  const { data } = await api.get<User[]>("/users");
  return data;
}

export async function fetchDashboardSummary() {
  const { data } = await api.get<DashboardSummary>("/dashboard/summary");
  return data;
}

export async function fetchIssues(params: Record<string, string | undefined> = {}) {
  const { data } = await api.get<IssueListResponse>("/issues", { params });
  return data.items;
}

export async function fetchNotifications() {
  const { data } = await api.get<NotificationListResponse>("/notifications", { params: { limit: 30 } });
  return data.items;
}

export async function fetchUnreadCount() {
  const { data } = await api.get<{ count: number }>("/notifications/unread-count");
  return data.count;
}

export async function markNotificationRead(id: string) {
  await api.post(`/notifications/${id}/read`);
}

export async function markAllNotificationsRead() {
  await api.post("/notifications/read-all");
}

export async function registerDevice(expoPushToken: string, platform: string) {
  await api.post("/devices/register", { expo_push_token: expoPushToken, platform });
}

export async function unregisterDevice(expoPushToken: string) {
  await api.post("/devices/unregister", { expo_push_token: expoPushToken });
}

export async function fetchIssue(id: string) {
  const { data } = await api.get<Issue>(`/issues/${id}`);
  return data;
}

export async function createIssue(payload: Record<string, unknown>) {
  const { data } = await api.post<Issue>("/issues", payload);
  return data;
}

export async function uploadIssuePhoto(
  issueId: string,
  uri: string,
  attachmentType: string,
  latitude?: number,
  longitude?: number
) {
  const form = new FormData();
  form.append("attachment_type", attachmentType);
  if (latitude !== undefined) form.append("latitude", String(latitude));
  if (longitude !== undefined) form.append("longitude", String(longitude));
  form.append("files", { uri, name: "photo.jpg", type: "image/jpeg" } as unknown as Blob);
  await api.post(`/issues/${issueId}/attachments`, form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
}

export async function submitIssue(id: string, report?: string) {
  const { data } = await api.post<Issue>(`/issues/${id}/submit`, { report });
  return data;
}

export async function updateIssue(id: string, payload: Record<string, unknown>) {
  const { data } = await api.patch<Issue>(`/issues/${id}`, payload);
  return data;
}

export async function parseVoice(uri: string) {
  const form = new FormData();
  form.append("file", { uri, name: "voice.m4a", type: "audio/m4a" } as unknown as Blob);
  const { data } = await api.post<VoiceDraft>("/voice/parse", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}

export async function setPersonalControl(id: string, on: boolean, importance = "NORMAL") {
  const { data } = await api.post<Issue>(`/issues/${id}/personal-control`, { on, importance });
  return data;
}

export async function transitionIssue(id: string, status: string) {
  const { data } = await api.post<Issue>(`/issues/${id}/transition`, { status });
  return data;
}

export async function fetchMapIssues(bbox = "69.05,54.80,69.25,54.94") {
  const { data } = await api.get<{ features: Array<{ id: string; geometry: { coordinates: [number, number] }; properties: Record<string, string | boolean | null> }> }>("/map/issues", {
    params: { bbox }
  });
  return data.features;
}

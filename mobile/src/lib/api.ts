import Constants from "expo-constants";
import axios from "axios";

import { useAuthStore } from "../store/auth";
import type { CatalogItem, Issue, IssueListResponse, NotificationListResponse, TokenPair, User } from "../types";

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

export async function fetchIssues() {
  const { data } = await api.get<IssueListResponse>("/issues");
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

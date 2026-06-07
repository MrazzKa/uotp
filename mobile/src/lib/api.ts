import Constants from "expo-constants";
import axios from "axios";

import { useAuthStore } from "../store/auth";
import type { TokenPair, User } from "../types";

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

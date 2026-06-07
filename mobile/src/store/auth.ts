import * as SecureStore from "expo-secure-store";
import { create } from "zustand";

import type { TokenPair, User } from "../types";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  setTokens: (tokens: TokenPair) => Promise<void>;
  setUser: (user: User | null) => void;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  setTokens: async (tokens) => {
    await SecureStore.setItemAsync("uotp.access", tokens.access_token);
    await SecureStore.setItemAsync("uotp.refresh", tokens.refresh_token);
    set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
  },
  setUser: (user) => set({ user }),
  logout: async () => {
    await SecureStore.deleteItemAsync("uotp.access");
    await SecureStore.deleteItemAsync("uotp.refresh");
    set({ accessToken: null, refreshToken: null, user: null });
  }
}));

export async function loadTokens() {
  const [accessToken, refreshToken] = await Promise.all([
    SecureStore.getItemAsync("uotp.access"),
    SecureStore.getItemAsync("uotp.refresh")
  ]);
  useAuthStore.setState({ accessToken, refreshToken });
}

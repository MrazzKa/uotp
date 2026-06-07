import { create } from "zustand";

import type { TokenPair, User } from "../types";

type AuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  setTokens: (tokens: TokenPair) => void;
  setUser: (user: User | null) => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem("uotp.access"),
  refreshToken: localStorage.getItem("uotp.refresh"),
  user: null,
  setTokens: (tokens) => {
    localStorage.setItem("uotp.access", tokens.access_token);
    localStorage.setItem("uotp.refresh", tokens.refresh_token);
    set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem("uotp.access");
    localStorage.removeItem("uotp.refresh");
    set({ accessToken: null, refreshToken: null, user: null });
  }
}));

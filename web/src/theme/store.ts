import { create } from "zustand";

type Theme = "light" | "dark";

export const useThemeStore = create<{
  theme: Theme;
  toggleTheme: () => void;
}>((set, get) => ({
  theme: (localStorage.getItem("uotp.theme") as Theme | null) ?? "light",
  toggleTheme: () => {
    const next = get().theme === "light" ? "dark" : "light";
    localStorage.setItem("uotp.theme", next);
    document.documentElement.classList.toggle("dark", next === "dark");
    set({ theme: next });
  }
}));

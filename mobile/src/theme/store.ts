import { create } from "zustand";

const palettes = {
  light: {
    background: "#f8fafc",
    text: "#172033",
    mutedText: "#64748b",
    border: "#d7dee8",
    primary: "#18808a",
    accent: "#d79b18",
    muted: "#e9eef5"
  },
  dark: {
    background: "#171b24",
    text: "#f4f7fb",
    mutedText: "#9aa8ba",
    border: "#343b49",
    primary: "#2fb8ae",
    accent: "#d69b24",
    muted: "#252b36"
  }
};

type Theme = keyof typeof palettes;

export const useThemeStore = create<{
  theme: Theme;
  colors: typeof palettes.light;
  toggleTheme: () => void;
}>((set, get) => ({
  theme: "light",
  colors: palettes.light,
  toggleTheme: () => {
    const theme = get().theme === "light" ? "dark" : "light";
    set({ theme, colors: palettes[theme] });
  }
}));

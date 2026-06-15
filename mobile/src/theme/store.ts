import { ColorSchemeName } from "react-native";
import { create } from "zustand";

import { palettes, ThemeColors, ThemeName } from "./tokens";

type ThemeMode = "system" | ThemeName;

function resolveTheme(mode: ThemeMode, systemScheme: ColorSchemeName | null | undefined): ThemeName {
  if (mode !== "system") return mode;
  return systemScheme === "dark" ? "dark" : "light";
}

export const useThemeStore = create<{
  mode: ThemeMode;
  theme: ThemeName;
  colors: ThemeColors;
  setSystemScheme: (scheme: ColorSchemeName | null | undefined) => void;
  toggleTheme: () => void;
}>((set, get) => ({
  mode: "system",
  theme: "light",
  colors: palettes.light,
  setSystemScheme: (scheme) => {
    const theme = resolveTheme(get().mode, scheme);
    set({ theme, colors: palettes[theme] });
  },
  toggleTheme: () => {
    const next: ThemeName = get().theme === "light" ? "dark" : "light";
    set({ mode: next, theme: next, colors: palettes[next] });
  }
}));

export function useTheme() {
  return useThemeStore((state) => ({
    mode: state.mode,
    theme: state.theme,
    colors: state.colors,
    toggleTheme: state.toggleTheme
  }));
}

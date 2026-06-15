import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useFonts, Inter_400Regular, Inter_500Medium, Inter_600SemiBold } from "@expo-google-fonts/inter";
import { Stack } from "expo-router";
import { useEffect } from "react";
import { Appearance } from "react-native";

import "../src/i18n";
import { useThemeStore } from "../src/theme/store";

const queryClient = new QueryClient();

export default function Layout() {
  const [fontsLoaded] = useFonts({ Inter_400Regular, Inter_500Medium, Inter_600SemiBold });
  const setSystemScheme = useThemeStore((state) => state.setSystemScheme);

  useEffect(() => {
    setSystemScheme(Appearance.getColorScheme());
    const subscription = Appearance.addChangeListener(({ colorScheme }) => setSystemScheme(colorScheme));
    return () => subscription.remove();
  }, [setSystemScheme]);

  if (!fontsLoaded) {
    return null;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Stack screenOptions={{ headerShown: false }} />
    </QueryClientProvider>
  );
}

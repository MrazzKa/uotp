import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";

import "../src/i18n";

const queryClient = new QueryClient();

export default function Layout() {
  return (
    <QueryClientProvider client={queryClient}>
      <Stack screenOptions={{ headerShown: false }} />
    </QueryClientProvider>
  );
}

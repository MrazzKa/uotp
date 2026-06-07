import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { fetchMe } from "./lib/api";
import { LoginPage } from "./pages/LoginPage";
import { RoleDashboard } from "./pages/dashboards/RoleDashboard";
import { useAuthStore } from "./store/auth";
import { useThemeStore } from "./theme/store";

export default function App() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
  const theme = useThemeStore((state) => state.theme);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    enabled: Boolean(accessToken) && !user,
    retry: false
  });

  if (!accessToken || !user) {
    return <LoginPage />;
  }

  return <RoleDashboard role={user.role.code} />;
}

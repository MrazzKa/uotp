import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { fetchMe } from "./lib/api";
import { LoginPage } from "./pages/LoginPage";
import { AdminPage } from "./pages/admin/AdminPage";
import { RoleDashboard } from "./pages/dashboards/RoleDashboard";
import { IssuesPage } from "./pages/issues/IssuesPage";
import { ProfilePage } from "./pages/profile/ProfilePage";
import { useAuthStore } from "./store/auth";
import { useThemeStore } from "./theme/store";

const MapPage = lazy(() => import("./pages/map/MapPage").then((module) => ({ default: module.MapPage })));
const StyleguidePage = lazy(() => import("./pages/styleguide/StyleguidePage").then((module) => ({ default: module.StyleguidePage })));

function PanelFallback({ text }: { text: string }) {
  return <div className="rounded-panel border border-border bg-surface p-5 shadow-card">{text}</div>;
}

export default function App() {
  const { t } = useTranslation();
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

  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<RoleDashboard role={user.role.code} />} />
        <Route path="/issues/*" element={<IssuesPage />} />
        <Route path="/admin" element={user.role.code === "ADMIN" ? <AdminPage /> : <Navigate to="/" replace />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route
          path="/map"
          element={
            <Suspense fallback={<PanelFallback text={t("loadingMap")} />}>
              <MapPage />
            </Suspense>
          }
        />
        <Route
          path="/styleguide"
          element={
            <Suspense fallback={<PanelFallback text={t("loading")} />}>
              <StyleguidePage />
            </Suspense>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

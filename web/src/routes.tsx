import { LoginPage } from "./pages/LoginPage";
import { RoleDashboard } from "./pages/dashboards/RoleDashboard";
import type { RoleCode } from "./types";

export function loginRoute() {
  return <LoginPage />;
}

export function dashboardRoute(role: RoleCode) {
  return <RoleDashboard role={role} />;
}

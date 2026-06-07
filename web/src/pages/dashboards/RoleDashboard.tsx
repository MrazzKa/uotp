import { LogOut, Moon, Sun } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "../../components/ui/Button";
import { useAuthStore } from "../../store/auth";
import { useThemeStore } from "../../theme/store";
import type { RoleCode } from "../../types";

const roleTitles: Record<RoleCode, string> = {
  ADMIN: "admin",
  DISPATCHER: "dispatcher",
  EXECUTOR: "executor",
  AKIM: "akim",
  INSPECTOR: "inspector"
};

const roleItems: Record<RoleCode, string[]> = {
  ADMIN: ["people", "queue"],
  DISPATCHER: ["queue", "checks"],
  EXECUTOR: ["nextTask", "checks"],
  AKIM: ["briefing", "queue"],
  INSPECTOR: ["checks", "queue"]
};

export function RoleDashboard({ role }: { role: RoleCode }) {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { theme, toggleTheme } = useThemeStore();

  function toggleLanguage() {
    const next = i18n.language === "ru" ? "kk" : "ru";
    localStorage.setItem("uotp.lng", next);
    i18n.changeLanguage(next);
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div>
            <p className="text-sm text-foreground/60">{user?.tenant.name_ru}</p>
            <h1 className="text-2xl font-semibold">{t(roleTitles[role])}</h1>
          </div>
          <div className="flex gap-2">
            <Button type="button" onClick={toggleTheme} title={t("theme")} className="w-10 px-0">
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </Button>
            <Button type="button" onClick={toggleLanguage} variant="accent">
              {t("language")}
            </Button>
            <Button type="button" onClick={logout} variant="muted">
              <LogOut size={18} />
              {t("signOut")}
            </Button>
          </div>
        </div>
      </header>
      <section className="mx-auto grid max-w-6xl gap-4 px-4 py-8 md:grid-cols-2">
        {roleItems[role].map((item) => (
          <article key={item} className="rounded-lg border border-border bg-muted p-5">
            <h2 className="text-lg font-semibold">{t(item)}</h2>
            <p className="mt-2 text-sm text-foreground/65">Foundation placeholder</p>
          </article>
        ))}
      </section>
    </main>
  );
}

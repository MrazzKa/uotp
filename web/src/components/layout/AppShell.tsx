import {
  Bell,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Map,
  Moon,
  Palette,
  Search,
  Sun
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ReactNode, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { Button } from "../ui/Button";
import { Tooltip } from "../ui/Tooltip";
import {
  fetchNotifications,
  fetchUnreadCount,
  logout as logoutApi,
  markAllNotificationsRead,
  markNotificationRead
} from "../../lib/api";
import { cn } from "../../lib/utils";
import { useAuthStore } from "../../store/auth";
import { useThemeStore } from "../../theme/store";
import type { NotificationItem } from "../../types";

type NavItem = {
  labelKey: string;
  href: string;
  icon: typeof LayoutDashboard;
};

const navItems: NavItem[] = [
  { labelKey: "dashboard", href: "/", icon: LayoutDashboard },
  { labelKey: "issues", href: "/issues", icon: ClipboardList },
  { labelKey: "map", href: "/map", icon: Map },
  { labelKey: "styleguide", href: "/styleguide", icon: Palette }
];

function pageTitle(pathname: string) {
  if (pathname.startsWith("/issues")) return "issues";
  if (pathname.startsWith("/map")) return "map";
  if (pathname.startsWith("/styleguide")) return "styleguide";
  return "dashboard";
}

export function AppShell({ children }: { children: ReactNode }) {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const { theme, toggleTheme } = useThemeStore();
  const [collapsed, setCollapsed] = useState(localStorage.getItem("uotp.sidebar") === "collapsed");
  const active = useLocation().pathname;
  const titleKey = pageTitle(active);
  const visibleNav = useMemo(() => navItems, []);

  function toggleSidebar() {
    const next = !collapsed;
    localStorage.setItem("uotp.sidebar", next ? "collapsed" : "expanded");
    setCollapsed(next);
  }

  function toggleLanguage() {
    const next = i18n.language === "ru" ? "kk" : "ru";
    localStorage.setItem("uotp.lng", next);
    i18n.changeLanguage(next);
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside
        className={cn(
          "fixed left-3 top-3 z-30 hidden h-[calc(100vh-24px)] flex-col rounded-r-[28px] rounded-l-panel border border-border bg-surface/95 p-3 shadow-raised backdrop-blur md:flex",
          collapsed ? "w-[76px]" : "w-[248px]"
        )}
      >
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-control bg-primary text-white shadow-base">
            U
          </div>
          {!collapsed ? (
            <div className="min-w-0">
              <p className="text-sm font-semibold leading-tight">UOTP</p>
              <p className="truncate text-xs text-mutedText">{user?.tenant.name_ru}</p>
            </div>
          ) : null}
        </div>

        <nav className="mt-6 grid gap-6">
          <NavGroup title={t("navigation")} collapsed={collapsed}>
            {visibleNav.map((item) => (
              <NavLink key={item.href} item={item} active={active} collapsed={collapsed} />
            ))}
          </NavGroup>
        </nav>

        <div className="mt-auto grid gap-2">
          <Tooltip content={collapsed ? t("collapse") : t("collapse")}>
            <Button type="button" variant="ghost" size="icon" onClick={toggleSidebar}>
              {collapsed ? <ChevronRight /> : <ChevronLeft />}
            </Button>
          </Tooltip>
        </div>
      </aside>

      <div className={cn("min-h-screen transition-[padding] duration-200", collapsed ? "md:pl-[100px]" : "md:pl-[272px]")}>
        <header className="sticky top-0 z-20 border-b border-border/80 bg-background/85 backdrop-blur">
          <div className="flex min-h-16 items-center justify-between gap-4 px-4 md:px-6">
            <div className="min-w-0">
              <p className="text-xs text-mutedText">{user?.tenant.name_ru}</p>
              <h1 className="truncate text-2xl font-semibold leading-tight">{t(titleKey)}</h1>
            </div>
            <div className="flex items-center gap-2">
              <div className="hidden h-10 min-w-[220px] items-center gap-2 rounded-chip border border-border bg-surface px-3 text-sm text-mutedText shadow-base lg:flex">
                <Search className="h-4 w-4 stroke-[1.6]" />
                {t("search")}
              </div>
              <Button type="button" variant="secondary" size="sm" onClick={toggleLanguage}>
                {i18n.language === "ru" ? "RU" : "KK"}
              </Button>
              <NotificationBell />
              <Tooltip content={t("theme")}>
                <Button type="button" variant="secondary" size="icon" onClick={toggleTheme}>
                  {theme === "light" ? <Moon /> : <Sun />}
                </Button>
              </Tooltip>
              <Button type="button" variant="ghost" size="sm" onClick={() => logoutApi()}>
                <LogOut />
                <span className="hidden sm:inline">{t("signOut")}</span>
              </Button>
            </div>
          </div>
        </header>
        <div className="px-4 py-6 md:px-6">{children}</div>
      </div>
    </div>
  );
}

function NotificationBell() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const count = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: fetchUnreadCount,
    refetchInterval: 30000
  });
  const notifications = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: () => fetchNotifications({ limit: 8 }),
    enabled: open,
    refetchInterval: open ? 30000 : false
  });
  const readOne = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    }
  });
  const readAll = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    }
  });

  async function openNotification(item: NotificationItem) {
    if (!item.is_read) {
      await readOne.mutateAsync(item.id);
    }
    if (item.issue_id) {
      navigate(`/issues/${item.issue_id}`);
    }
  }

  return (
    <div className="relative">
      <Tooltip content={t("notifications")}>
        <Button type="button" variant="secondary" size="icon" onClick={() => setOpen((value) => !value)}>
          <Bell />
          {(count.data ?? 0) > 0 ? (
            <span className="absolute -right-1 -top-1 grid min-h-5 min-w-5 place-items-center rounded-full bg-danger px-1 text-[11px] font-semibold text-white">
              {Math.min(count.data ?? 0, 99)}
            </span>
          ) : null}
        </Button>
      </Tooltip>
      {open ? (
        <div className="absolute right-0 top-12 z-40 w-[min(360px,calc(100vw-32px))] overflow-hidden rounded-panel border border-border bg-surface shadow-raised">
          <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
            <p className="text-sm font-semibold">{t("notifications")}</p>
            <Button type="button" variant="ghost" size="sm" onClick={() => readAll.mutate()}>
              <CheckCheck />
              {t("markAllRead")}
            </Button>
          </div>
          <div className="max-h-[420px] overflow-y-auto p-2">
            {(notifications.data?.items ?? []).length ? (
              notifications.data?.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={cn(
                    "grid w-full gap-1 rounded-control p-3 text-left transition hover:bg-surface2",
                    !item.is_read ? "bg-primarySoft/60" : ""
                  )}
                  onClick={() => openNotification(item)}
                >
                  <span className="flex items-start justify-between gap-3">
                    <span className="text-sm font-semibold text-foreground">{item.title}</span>
                    {!item.is_read ? <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" /> : null}
                  </span>
                  <span className="text-sm text-mutedText">{item.body}</span>
                  <span className="text-xs text-mutedText">{new Date(item.created_at).toLocaleString()}</span>
                </button>
              ))
            ) : (
              <p className="px-3 py-8 text-center text-sm text-mutedText">{t("noNotifications")}</p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function NavGroup({
  title,
  collapsed,
  children
}: {
  title: string;
  collapsed: boolean;
  children: ReactNode;
}) {
  return (
    <div className="grid gap-2">
      {!collapsed ? <p className="px-3 text-xs font-medium text-mutedText">{title}</p> : null}
      <div className="grid gap-1">{children}</div>
    </div>
  );
}

function NavLink({ item, active, collapsed }: { item: NavItem; active: string; collapsed: boolean }) {
  const { t } = useTranslation();
  const isActive = item.href === "/" ? active === "/" : active.startsWith(item.href);
  const Icon = item.icon;
  const content = (
    <Link
      className={cn(
        "flex h-10 items-center gap-3 rounded-control px-3 text-sm font-medium transition [&_svg]:stroke-[1.65]",
        collapsed ? "justify-center px-0" : "",
        isActive ? "bg-primarySoft text-primary" : "text-mutedText hover:bg-surface2 hover:text-foreground"
      )}
      to={item.href}
    >
      <Icon className="h-[18px] w-[18px] shrink-0" />
      {!collapsed ? <span>{t(item.labelKey)}</span> : null}
    </Link>
  );
  return collapsed ? <Tooltip content={t(item.labelKey)}>{content}</Tooltip> : content;
}

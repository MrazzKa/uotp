import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ClipboardList, Clock3, Inbox, ShieldCheck, X } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { StatusPill } from "../../components/ui/Badge";
import { Card, Panel } from "../../components/ui/Card";
import { SoftDonutChart, SoftLineChart } from "../../components/ui/Charts";
import { KPICard } from "../../components/ui/KPICard";
import { ProgressBar } from "../../components/ui/Progress";
import { fetchDashboardSummary, fetchIssues, fetchOkrugDetail } from "../../lib/api";
import { statusHex } from "../../lib/design";
import { useAuthStore } from "../../store/auth";
import type { DashboardSummary, Issue, OkrugBreakdown, RoleCode } from "../../types";

const roleTitles: Record<RoleCode, string> = {
  ADMIN: "admin",
  AKIM: "akim",
  DEPUTY: "deputy",
  APPARAT: "apparat",
  DEPT_HEAD: "deptHead",
  AKIM_SO: "akimSo",
  SPECIALIST: "specialist",
  OPERATOR: "operator",
  CONTRACTOR: "contractor"
};

const EXECUTIVE_ROLES: RoleCode[] = ["AKIM", "DEPUTY", "APPARAT", "ADMIN"];
const PERSONAL_ROLES: RoleCode[] = ["SPECIALIST", "CONTRACTOR"];

function countsFromIssues(items: Issue[]) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const withStatus = (status: string) => items.filter((issue) => issue.status === status).length;
  return {
    in_progress: withStatus("ASSIGNED"),
    overdue: items.filter((issue) => issue.is_overdue).length,
    on_review: items.filter((issue) => issue.status === "REVIEW_CONTROLLER" || issue.status === "REVIEW_AUTHOR").length,
    closed_today: items.filter((issue) => issue.status === "CLOSED" && issue.closed_at && new Date(issue.closed_at) >= today).length,
    new: withStatus("NEW")
  };
}

export function RoleDashboard({ role }: { role: RoleCode }) {
  const { t } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const summary = useQuery({ queryKey: ["dashboard-summary"], queryFn: fetchDashboardSummary });
  const executive = EXECUTIVE_ROLES.includes(role);
  const personal = PERSONAL_ROLES.includes(role);
  // У исполнительских ролей KPI считаем «по мне» (согласовано с панелью «Мои задачи»),
  // чтобы цифры плиток совпадали со списком, а не с общим срезом по сфере.
  const showMineKpi = !executive && role !== "OPERATOR";
  const mineForKpi = useQuery({
    queryKey: ["dashboard-mine-kpi"],
    queryFn: () => fetchIssues({ mine: "true", limit: "100" }),
    enabled: showMineKpi
  });
  const data = summary.data;

  if (!data) {
    return <Panel>{t("loading")}</Panel>;
  }

  const counts = showMineKpi && mineForKpi.data ? countsFromIssues(mineForKpi.data.items) : data.counts;

  const hour = new Date().getHours();
  const greeting = hour < 12 ? t("greetingMorning") : hour < 18 ? t("greetingDay") : t("greetingEvening");
  const firstName = user?.full_name?.split(" ")[0];

  return (
    <main className="mx-auto grid max-w-7xl gap-6">
      <div>
        <p className="text-sm text-mutedText">{t(roleTitles[role])}</p>
        <h2 className="text-[30px] font-semibold leading-tight">{firstName ? `${greeting}, ${firstName}` : greeting}</h2>
        <p className="mt-1 text-sm text-mutedText">
          {personal ? t("personalSummary") : executive ? t("executiveDashboard") : t("operationsDashboard")}
        </p>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <KPICard label={t("inProgress")} value={counts.in_progress} tone="primary" icon={Clock3} />
        <KPICard label={t("overdue")} value={counts.overdue} tone="danger" icon={AlertTriangle} />
        <KPICard label={t("inspectionCount")} value={counts.on_review} tone="warning" icon={ShieldCheck} />
        <KPICard label={t("closedToday")} value={counts.closed_today} tone="success" icon={CheckCircle2} />
        <KPICard label={t("new")} value={counts.new} tone="info" icon={Inbox} />
      </section>

      {executive ? (
        <>
          {data.okrug_monitoring?.length ? <OkrugMonitoring data={data.okrug_monitoring} /> : null}

          <IssueListPanel title={t("onlyPersonal")} params={{ personal: "true" }} grouped />

          <section className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
            <Panel>
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold">{t("tasksByDay")}</h3>
                  <p className="text-sm text-mutedText">{t("last14Days")}</p>
                </div>
                <ClipboardList className="h-5 w-5 text-mutedText stroke-[1.6]" />
              </div>
              <SoftLineChart data={data.per_day} xKey="date" yKey="count" />
            </Panel>

            <Panel>
              <h3 className="text-base font-semibold">{t("slaOnTime")}</h3>
              <div className="mt-5">
                <p className="text-[44px] font-semibold leading-none">{data.sla_on_time_pct}%</p>
                <p className="mt-2 text-sm text-mutedText">{t("slaTarget")}</p>
              </div>
              <ProgressBar value={data.sla_on_time_pct} className="mt-5" />
            </Panel>
          </section>

          <section className="grid gap-4 xl:grid-cols-2">
            <Panel>
              <h3 className="mb-4 text-base font-semibold">{t("byStatus")}</h3>
              <SoftDonutChart data={data.by_status} nameKey="status" valueKey="count" />
              <div className="mt-4 grid gap-2">
                {data.by_status.map((row) => (
                  <div key={String(row.status)} className="flex items-center justify-between gap-3 text-sm">
                    <span className="inline-flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: statusHex(String(row.status)) }} />
                      {t(`st_${row.status}`, String(row.status))}
                    </span>
                    <span className="font-medium text-mutedText">{row.count}</span>
                  </div>
                ))}
              </div>
            </Panel>
            <RecentEvents data={data} />
          </section>
        </>
      ) : (
        <section className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
          {role === "OPERATOR" ? (
            <IssueListPanel title={t("unassignedQueue")} params={{ status: "NEW" }} hint={t("unassignedHint")} />
          ) : (
            <IssueListPanel title={t("myTasks")} params={{ mine: "true" }} />
          )}
          <RecentEvents data={data} />
        </section>
      )}
    </main>
  );
}

function IssueRow({ issue }: { issue: Issue }) {
  const { i18n } = useTranslation();
  return (
    <Link to={`/issues/${issue.id}`} className="flex items-center justify-between gap-3 rounded-control bg-surface2 p-3 transition hover:bg-surface2/70">
      <div className="min-w-0">
        <p className="truncate font-medium">{issue.title}</p>
        <p className="text-xs text-mutedText">
          {issue.public_number}
          {issue.sphere ? ` · ${i18n.language === "kk" ? issue.sphere.name_kk : issue.sphere.name_ru}` : ""}
        </p>
      </div>
      <StatusPill status={issue.status} isOverdue={issue.is_overdue} />
    </Link>
  );
}

// Группировка «Мой контроль» по стадии жизненного цикла (спецификация 6.2-6.3).
const CONTROL_GROUPS: { key: string; statuses: string[] }[] = [
  { key: "groupInWork", statuses: ["NEW", "ASSIGNED", "ON_HOLD", "DRAFT"] },
  { key: "groupAtController", statuses: ["REVIEW_CONTROLLER"] },
  { key: "groupForRemoval", statuses: ["REVIEW_AUTHOR"] }
];

function IssueListPanel({ title, params, hint, grouped }: { title: string; params: Record<string, string>; hint?: string; grouped?: boolean }) {
  const { t } = useTranslation();
  const query = useQuery({ queryKey: ["issues", params], queryFn: () => fetchIssues({ ...params, limit: "20" }) });
  const items = query.data?.items ?? [];
  return (
    <Panel>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-base font-semibold">{title}</h3>
        {items.length ? <span className="rounded-chip bg-surface2 px-2.5 py-1 text-xs font-medium text-mutedText">{items.length}</span> : null}
      </div>
      {hint && items.length ? <p className="-mt-2 mb-3 text-xs text-mutedText">{hint}</p> : null}
      {items.length ? (
        grouped ? (
          <div className="grid gap-4">
            {CONTROL_GROUPS.map((group) => {
              const groupItems = items.filter((issue) => group.statuses.includes(issue.status));
              if (!groupItems.length) return null;
              return (
                <div key={group.key}>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-mutedText">{t(group.key)} · {groupItems.length}</p>
                  <div className="grid gap-2">
                    {groupItems.map((issue) => <IssueRow key={issue.id} issue={issue} />)}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="grid gap-2">
            {items.map((issue) => <IssueRow key={issue.id} issue={issue} />)}
          </div>
        )
      ) : (
        <p className="text-sm text-mutedText">{t("emptyState")}</p>
      )}
    </Panel>
  );
}

function okrugTone(pct: number) {
  if (pct >= 85) return { badge: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200", bar: "bg-emerald-500" };
  if (pct >= 65) return { badge: "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-200", bar: "bg-amber-500" };
  return { badge: "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-200", bar: "bg-red-500" };
}

function OkrugMonitoring({ data }: { data: DashboardSummary["okrug_monitoring"] }) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<{ id: string; name: string } | null>(null);
  return (
    <Panel>
      <h3 className="mb-4 text-base font-semibold">{t("okrugMonitoring")}</h3>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {data.map((okrug) => {
          const c = okrugTone(okrug.pct);
          return (
            <button
              key={okrug.name}
              type="button"
              disabled={!okrug.id}
              onClick={() => okrug.id && setSelected({ id: okrug.id, name: okrug.name })}
              className="rounded-control border border-border bg-surface2 p-3 text-left transition hover:border-primary/60 disabled:cursor-default"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-medium">{okrug.name}</p>
                  <p className="text-xs text-mutedText">{okrug.done} {t("ofTasks")} {okrug.total}</p>
                </div>
                <span className={`rounded-chip px-2 py-1 text-sm font-semibold ${c.badge}`}>{okrug.pct}%</span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-border">
                <div className={`h-full ${c.bar}`} style={{ width: `${okrug.pct}%` }} />
              </div>
            </button>
          );
        })}
      </div>
      {selected ? <OkrugDetailModal id={selected.id} name={selected.name} onClose={() => setSelected(null)} /> : null}
    </Panel>
  );
}

function OkrugDetailModal({ id, name, onClose }: { id: string; name: string; onClose: () => void }) {
  const { t } = useTranslation();
  const detail = useQuery({ queryKey: ["okrug", id], queryFn: () => fetchOkrugDetail(id) });
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-panel border border-border bg-surface p-5 shadow-raised" onClick={(event) => event.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">{name}</h3>
          <button type="button" onClick={onClose} className="rounded-control p-2 text-mutedText transition hover:bg-surface2"><X size={18} /></button>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <BreakdownList title={t("bySpecialists")} rows={detail.data?.by_user ?? []} />
          <BreakdownList title={t("bySpheres")} rows={detail.data?.by_sphere ?? []} />
        </div>
      </div>
    </div>
  );
}

function BreakdownList({ title, rows }: { title: string; rows: OkrugBreakdown[] }) {
  const { t } = useTranslation();
  return (
    <div>
      <h4 className="mb-3 text-sm font-semibold text-mutedText">{title}</h4>
      {rows.length ? (
        <div className="grid gap-2">
          {rows.map((row) => {
            const c = okrugTone(row.pct);
            return (
              <div key={row.name} className="grid gap-1">
                <div className="flex items-center justify-between gap-2 text-sm">
                  <span className="truncate">{row.name}</span>
                  <span className="shrink-0 text-mutedText">{row.done} {t("ofTasks")} {row.total} · {row.pct}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-border">
                  <div className={`h-full ${c.bar}`} style={{ width: `${row.pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-mutedText">-</p>
      )}
    </div>
  );
}

function RecentEvents({ data }: { data: DashboardSummary }) {
  const { t } = useTranslation();
  return (
    <Panel>
      <h3 className="mb-4 text-base font-semibold">{t("recentEvents")}</h3>
      <div className="grid gap-3">
        {data.recent_events.length ? (
          data.recent_events.map((event) => (
            <Link key={`${event.issue_id}-${event.created_at}`} className="grid gap-1 rounded-control bg-surface2 p-3" to={`/issues/${event.issue_id}`}>
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">{event.public_number}</span>
                {event.to_status ? <StatusPill status={event.to_status} /> : null}
              </div>
              <p className="text-sm text-mutedText">{t(`ev_${event.action}`, event.action)}</p>
              <p className="text-xs text-mutedText">{new Date(event.created_at).toLocaleString()}</p>
            </Link>
          ))
        ) : (
          <p className="text-sm text-mutedText">{t("emptyState")}</p>
        )}
      </div>
    </Panel>
  );
}

function HotZones({ data }: { data: DashboardSummary }) {
  const { t } = useTranslation();
  const max = Math.max(...data.hot_zones.map((zone) => zone.count), 1);
  return (
    <Panel>
      <h3 className="mb-4 text-base font-semibold">{t("hotZones")}</h3>
      <div className="grid gap-3">
        {data.hot_zones.length ? (
          data.hot_zones.map((zone) => (
            <div key={zone.district_id ?? zone.name} className="grid gap-2">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium">{zone.name}</span>
                <span className="text-mutedText">{zone.count}</span>
              </div>
              <ProgressBar value={(zone.count / max) * 100} />
            </div>
          ))
        ) : (
          <p className="text-sm text-mutedText">{t("emptyState")}</p>
        )}
      </div>
    </Panel>
  );
}

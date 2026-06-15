import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ClipboardList, Clock3, Inbox, ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { StatusPill } from "../../components/ui/Badge";
import { Card, Panel } from "../../components/ui/Card";
import { SoftBarChart, SoftDonutChart, SoftLineChart } from "../../components/ui/Charts";
import { KPICard } from "../../components/ui/KPICard";
import { ProgressBar } from "../../components/ui/Progress";
import { fetchDashboardSummary } from "../../lib/api";
import type { DashboardSummary, RoleCode } from "../../types";

const roleTitles: Record<RoleCode, string> = {
  ADMIN: "admin",
  DISPATCHER: "dispatcher",
  EXECUTOR: "executor",
  AKIM: "akim",
  INSPECTOR: "inspector"
};

export function RoleDashboard({ role }: { role: RoleCode }) {
  const { t } = useTranslation();
  const summary = useQuery({ queryKey: ["dashboard-summary"], queryFn: fetchDashboardSummary });
  const data = summary.data;

  if (!data) {
    return <Panel>{t("loading")}</Panel>;
  }

  const executive = role === "AKIM";
  const personal = role === "EXECUTOR";

  return (
    <main className="mx-auto grid max-w-7xl gap-6">
      <div>
        <p className="text-sm text-mutedText">{t(roleTitles[role])}</p>
        <h2 className="text-[28px] font-semibold leading-tight">
          {personal ? t("personalSummary") : executive ? t("executiveDashboard") : t("operationsDashboard")}
        </h2>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <KPICard label={t("inProgress")} value={data.counts.in_progress} icon={Clock3} />
        <KPICard label={t("overdue")} value={data.counts.overdue} icon={AlertTriangle} />
        <KPICard label={t("inspectionCount")} value={data.counts.inspection} icon={ShieldCheck} />
        <KPICard label={t("closedToday")} value={data.counts.closed_today} icon={CheckCircle2} />
        <KPICard label={t("new")} value={data.counts.new} icon={Inbox} />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
        <Panel>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold">{t("tasksByDay")}</h3>
              <p className="text-sm text-mutedText">{t("last14Days")}</p>
            </div>
            <ClipboardList className="h-5 w-5 text-mutedText stroke-[1.6]" />
          </div>
          {executive ? (
            <SoftLineChart data={data.per_day} xKey="date" yKey="count" />
          ) : (
            <SoftBarChart data={data.per_day} xKey="date" yKey="count" />
          )}
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

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1fr_1fr]">
        <Panel>
          <h3 className="mb-4 text-base font-semibold">{t("byStatus")}</h3>
          <SoftDonutChart data={data.by_status} nameKey="status" valueKey="count" />
        </Panel>
        {!executive ? <RecentEvents data={data} /> : <HotZones data={data} />}
        {!executive ? <HotZones data={data} /> : <RecentEvents data={data} />}
      </section>
    </main>
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
              <p className="text-sm text-mutedText">{event.action}</p>
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

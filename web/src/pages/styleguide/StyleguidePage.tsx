import { Activity, ClipboardList, Users } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Badge, StatusPill } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card, Panel } from "../../components/ui/Card";
import { SoftBarChart, SoftDonutChart, SoftLineChart } from "../../components/ui/Charts";
import { FieldLabel, Input, Select, Textarea } from "../../components/ui/Field";
import { KPICard } from "../../components/ui/KPICard";
import { DataTable, TableCell, TableHead, TableHeaderCell, TableRow } from "../../components/ui/Table";
import { chartPalette } from "../../lib/design";
import type { IssueStatus } from "../../types";

const statuses: IssueStatus[] = [
  "DRAFT",
  "NEW",
  "ASSIGNED",
  "REVIEW_CONTROLLER",
  "REVIEW_AUTHOR",
  "CLOSED",
  "ON_HOLD"
];

const trendData = [
  { day: "Mon", value: 18 },
  { day: "Tue", value: 24 },
  { day: "Wed", value: 21 },
  { day: "Thu", value: 32 },
  { day: "Fri", value: 28 },
  { day: "Sat", value: 35 },
  { day: "Sun", value: 41 }
];

const donutData = [
  { name: "Roads", value: 42 },
  { name: "Lighting", value: 28 },
  { name: "Parks", value: 18 },
  { name: "Other", value: 12 }
];

const tokens = [
  "bg",
  "surface",
  "surface-2",
  "primary",
  "success",
  "warning",
  "danger"
];

export function StyleguidePage() {
  const { t } = useTranslation();

  return (
    <main className="mx-auto grid max-w-7xl gap-6">
      <Panel>
        <p className="text-sm text-mutedText">{t("styleguideIntro")}</p>
        <h2 className="mt-2 text-[28px] font-semibold leading-tight">{t("designSystem")}</h2>
      </Panel>

      <section className="grid gap-4 md:grid-cols-4">
        <KPICard label={t("issues")} value="1,248" hint="+12% за месяц" icon={ClipboardList} />
        <KPICard label={t("people")} value="86" hint="+4% за месяц" tone="info" icon={Users} />
        <KPICard label={t("checks")} value="94%" hint="-2% за месяц" tone="warning" icon={Activity} />
        <Card>
          <p className="text-sm text-mutedText">{t("chartPalette")}</p>
          <div className="mt-4 flex gap-2">
            {chartPalette.map((color) => (
              <span key={color} className="h-9 w-9 rounded-chip border border-border" style={{ background: color }} />
            ))}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Panel>
          <h3 className="text-base font-semibold">{t("palette")}</h3>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {tokens.map((label) => (
              <div key={label} className="rounded-control border border-border bg-surface2 p-3">
                <div className="h-12 rounded-control" style={{ background: `var(--${label})` }} />
                <p className="mt-2 text-xs text-mutedText">--{label}</p>
              </div>
            ))}
          </div>
        </Panel>
        <Panel>
          <h3 className="text-base font-semibold">{t("typography")}</h3>
          <div className="mt-4 grid gap-3">
            <p className="text-[28px] font-semibold leading-tight">Display 28/600</p>
            <h1 className="text-2xl font-semibold">H1 24/600</h1>
            <h2 className="text-xl font-semibold">H2 20/600</h2>
            <h3 className="text-base font-semibold">H3 16/600</h3>
            <p className="text-sm">Body 14/400</p>
            <p className="text-[13px] text-mutedText">Small 13/400</p>
            <p className="text-xs text-mutedText">Caption 12/400</p>
          </div>
        </Panel>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Panel>
          <h3 className="text-base font-semibold">{t("components")}</h3>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button>{t("create")}</Button>
            <Button variant="secondary">{t("assign")}</Button>
            <Button variant="ghost">{t("cancel")}</Button>
            <Button variant="danger">{t("reject")}</Button>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            {statuses.map((status) => (
              <StatusPill key={status} status={status} />
            ))}
            <StatusPill status="IN_PROGRESS" isOverdue />
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge className="bg-primarySoft text-primary">{t("all")}</Badge>
            <Badge className="bg-surface2 text-mutedText">{t("protocols")}</Badge>
          </div>
        </Panel>
        <Panel>
          <h3 className="text-base font-semibold">{t("forms")}</h3>
          <div className="mt-4 grid gap-3">
            <FieldLabel label={t("title")}><Input placeholder={t("title")} /></FieldLabel>
            <FieldLabel label={t("status")}><Select><option>{t("status")}</option></Select></FieldLabel>
            <FieldLabel label={t("description")}><Textarea placeholder={t("description")} /></FieldLabel>
          </div>
        </Panel>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Panel><SoftLineChart data={trendData} xKey="day" yKey="value" /></Panel>
        <Panel><SoftBarChart data={trendData} xKey="day" yKey="value" /></Panel>
        <Panel><SoftDonutChart data={donutData} nameKey="name" valueKey="value" /></Panel>
      </section>

      <DataTable>
        <TableHead>
          <tr>
            <TableHeaderCell>{t("number")}</TableHeaderCell>
            <TableHeaderCell>{t("status")}</TableHeaderCell>
            <TableHeaderCell>{t("assignee")}</TableHeaderCell>
            <TableHeaderCell>{t("created")}</TableHeaderCell>
          </tr>
        </TableHead>
        <tbody>
          {["PVL-2026-00001", "PVL-2026-00002", "PVL-2026-00003"].map((number, index) => (
            <TableRow key={number}>
              <TableCell className="font-medium">{number}</TableCell>
              <TableCell><StatusPill status={statuses[index + 1]} /></TableCell>
              <TableCell>Maria K.</TableCell>
              <TableCell>14.06.2026</TableCell>
            </TableRow>
          ))}
        </tbody>
      </DataTable>
    </main>
  );
}

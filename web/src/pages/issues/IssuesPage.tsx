import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, ClipboardList, Plus, Search, Send, X } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";

import { AvatarInitials } from "../../components/ui/Avatar";
import { StatusPill } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { FilterChip } from "../../components/ui/FilterChip";
import { Input, Select, Textarea } from "../../components/ui/Field";
import { ProgressBar } from "../../components/ui/Progress";
import { DataTable, TableCell, TableHead, TableHeaderCell, TableRow } from "../../components/ui/Table";
import {
  addIssueComment,
  assignIssue,
  createIssue,
  fetchCatalogs,
  fetchIssue,
  fetchIssues,
  qualifyIssue,
  transitionIssue
} from "../../lib/api";
import { useAuthStore } from "../../store/auth";
import type { CatalogItem, Issue, RoleCode, User } from "../../types";

type View = { name: "list" } | { name: "new" } | { name: "detail"; id: string };

function pickName(item: CatalogItem | null | undefined, language: string) {
  if (!item) return "";
  return language === "kk" ? item.name_kk : item.name_ru;
}

function slaText(issue: Issue, overdueLabel: string) {
  if (issue.is_overdue) return overdueLabel;
  if (!issue.sla_due_at) return "";
  const minutes = Math.ceil((new Date(issue.sla_due_at).getTime() - Date.now()) / 60000);
  if (minutes < 0) return overdueLabel;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return hours > 0 ? `${hours}h ${rest}m` : `${rest}m`;
}

function slaClass(issue: Issue) {
  if (issue.is_overdue) return "bg-danger text-white";
  if (!issue.sla_due_at) return "bg-surface2 text-mutedText";
  const minutes = (new Date(issue.sla_due_at).getTime() - Date.now()) / 60000;
  if (minutes <= 360) return "bg-warning text-white";
  return "bg-primarySoft text-primary";
}

const progressByStatus: Record<string, number> = {
  NEW: 0,
  QUALIFICATION: 10,
  ASSIGNED: 25,
  ACCEPTED: 40,
  IN_PROGRESS: 60,
  COMPLETED: 85,
  INSPECTION: 95,
  CLOSED: 100
};

function issueProgress(issue: Issue) {
  return progressByStatus[issue.status] ?? 0;
}

function riskLevel(issue: Issue) {
  if (issue.is_overdue) return "high";
  if (!issue.sla_due_at || !issue.created_at) return "low";
  const created = new Date(issue.created_at).getTime();
  const due = new Date(issue.sla_due_at).getTime();
  const now = Date.now();
  const total = Math.max(due - created, 1);
  const remaining = due - now;
  if (remaining / total < 0.2) return "medium";
  return "low";
}

function transitionActions(role: RoleCode, issue: Issue) {
  if (role === "AKIM") return [];
  if (role === "ADMIN") {
    return [
      { status: "ACCEPTED", label: "accept", primary: issue.status === "ASSIGNED" },
      { status: "IN_PROGRESS", label: "onSite", primary: issue.status === "ACCEPTED" },
      { status: "COMPLETED", label: "complete", primary: issue.status === "IN_PROGRESS" },
      { status: "INSPECTION", label: "inspect", primary: issue.status === "COMPLETED" },
      { status: "CLOSED", label: "close", primary: issue.status === "INSPECTION" },
      { status: "REJECTED", label: "reject" },
      { status: "RETURNED", label: "return" }
    ];
  }
  const transitions: Partial<Record<RoleCode, Partial<Record<string, Array<{ status: string; label: string; primary?: boolean }>>>>> = {
    DISPATCHER: {
      NEW: [
        { status: "QUALIFICATION", label: "qualify", primary: true },
        { status: "REJECTED", label: "reject" }
      ],
      QUALIFICATION: [
        { status: "ASSIGNED", label: "assign", primary: true },
        { status: "REJECTED", label: "reject" }
      ],
      ASSIGNED: [{ status: "ASSIGNED", label: "assign", primary: true }]
    },
    EXECUTOR: {
      ASSIGNED: [{ status: "ACCEPTED", label: "accept", primary: true }],
      ACCEPTED: [{ status: "IN_PROGRESS", label: "onSite", primary: true }],
      IN_PROGRESS: [{ status: "COMPLETED", label: "complete", primary: true }]
    },
    INSPECTOR: {
      COMPLETED: [{ status: "INSPECTION", label: "inspect", primary: true }],
      INSPECTION: [
        { status: "CLOSED", label: "close", primary: true },
        { status: "RETURNED", label: "return" }
      ]
    }
  };
  return transitions[role]?.[issue.status] ?? [];
}

function pathForView(view: View): string {
  return view.name === "list" ? "/issues" : view.name === "new" ? "/issues/new" : `/issues/${view.id}`;
}

function viewFromPath(pathname: string): View {
  const parts = pathname.split("/").filter(Boolean);
  if (parts[0] !== "issues") return { name: "list" };
  if (parts[1] === "new") return { name: "new" };
  if (parts[1]) return { name: "detail", id: parts[1] };
  return { name: "list" };
}

export function IssuesPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const view = viewFromPath(location.pathname);
  const go = (next: View) => navigate(pathForView(next));

  if (!user) return null;

  return (
    <main className="min-h-screen">
      {view.name === "list" ? <IssueList onOpen={(id) => go({ name: "detail", id })} onNew={() => go({ name: "new" })} /> : null}
      {view.name === "new" ? <IssueCreate onBack={() => go({ name: "list" })} onCreated={(id) => go({ name: "detail", id })} /> : null}
      {view.name === "detail" ? <IssueDetail issueId={view.id} role={user.role.code} onBack={() => go({ name: "list" })} /> : null}
    </main>
  );
}

function IssueList({ onOpen, onNew }: { onOpen: (id: string) => void; onNew: () => void }) {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [category, setCategory] = useState("");
  const [district, setDistrict] = useState("");
  const [mode, setMode] = useState<"all" | "mine" | "overdue">("all");
  const [cursor, setCursor] = useState<string | undefined>();
  const [sortKey, setSortKey] = useState<"created" | "number">("created");
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const params = useMemo(
    () => ({
      q: q || undefined,
      status: status || undefined,
      priority: priority || undefined,
      category: category || undefined,
      district: district || undefined,
      is_overdue: mode === "overdue" ? "true" : undefined,
      assigned_to: mode === "mine" ? user?.id : undefined,
      cursor
    }),
    [q, status, priority, category, district, mode, user?.id, cursor]
  );
  const issues = useQuery({ queryKey: ["issues", params], queryFn: () => fetchIssues(params) });
  const items = useMemo(() => {
    const rows = [...(issues.data?.items ?? [])];
    return rows.sort((a, b) => {
      if (sortKey === "number") return a.public_number.localeCompare(b.public_number);
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }, [issues.data?.items, sortKey]);

  return (
    <>
      <section className="mx-auto max-w-7xl">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-1 flex-wrap gap-2">
            <FilterChip active={mode === "all"} onClick={() => { setMode("all"); setCursor(undefined); }}>{t("all")}</FilterChip>
            <FilterChip active={mode === "mine"} onClick={() => { setMode("mine"); setCursor(undefined); }}>{t("mine")}</FilterChip>
            <FilterChip active={mode === "overdue"} onClick={() => { setMode("overdue"); setCursor(undefined); }}>{t("onlyOverdue")}</FilterChip>
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-mutedText" />
              <Input className="pl-9" value={q} onChange={(event) => { setQ(event.target.value); setCursor(undefined); }} placeholder={t("search")} />
            </div>
            <Select value={status} onChange={(event) => { setStatus(event.target.value); setCursor(undefined); }}>
              <option value="">{t("status")}</option>
              {["NEW", "QUALIFICATION", "ASSIGNED", "ACCEPTED", "IN_PROGRESS", "COMPLETED", "INSPECTION", "CLOSED"].map((item) => <option key={item} value={item}>{item}</option>)}
            </Select>
            <Select value={priority} onChange={(event) => { setPriority(event.target.value); setCursor(undefined); }}>
              <option value="">{t("priority")}</option>
              {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((item) => <option key={item} value={item}>{item}</option>)}
            </Select>
            <Select value={category} onChange={(event) => { setCategory(event.target.value); setCursor(undefined); }}>
              <option value="">{t("category")}</option>
              {catalogs.data?.categories.map((item) => <option key={item.id} value={item.id}>{pickName(item, i18n.language)}</option>)}
            </Select>
            <Select value={district} onChange={(event) => { setDistrict(event.target.value); setCursor(undefined); }}>
              <option value="">{t("district")}</option>
              {catalogs.data?.districts.map((item) => <option key={item.id} value={item.id}>{pickName(item, i18n.language)}</option>)}
            </Select>
          </div>
          {user?.role.code === "ADMIN" || user?.role.code === "DISPATCHER" ? <Button onClick={onNew}><Plus size={18} />{t("newIssue")}</Button> : null}
        </div>
        <DataTable>
            <TableHead>
              <tr>
                <TableHeaderCell><button type="button" onClick={() => setSortKey("number")}>{t("number")}</button></TableHeaderCell>
                {["status", "category", "priority", "district", "sla", "assignee"].map((key) => <TableHeaderCell key={key}>{t(key)}</TableHeaderCell>)}
                <TableHeaderCell><button type="button" onClick={() => setSortKey("created")}>{t("created")}</button></TableHeaderCell>
              </tr>
            </TableHead>
            <tbody>
              {items.map((issue) => (
                <TableRow key={issue.id} className="cursor-pointer" onClick={() => onOpen(issue.id)}>
                  <TableCell className="font-medium">{issue.public_number}</TableCell>
                  <TableCell><StatusPill status={issue.status} isOverdue={issue.is_overdue} /></TableCell>
                  <TableCell>{pickName(issue.category, i18n.language)}</TableCell>
                  <TableCell>{issue.priority}</TableCell>
                  <TableCell>{pickName(issue.district, i18n.language)}</TableCell>
                  <TableCell><span className={`rounded-chip px-2.5 py-1 text-xs font-medium ${slaClass(issue)}`}>{slaText(issue, t("overdue")) || "-"}</span></TableCell>
                  <TableCell>
                    {issue.assigned_to ? (
                      <span className="inline-flex items-center gap-2">
                        <AvatarInitials name={issue.assigned_to.full_name} />
                        {issue.assigned_to.full_name}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell>{new Date(issue.created_at).toLocaleDateString()}</TableCell>
                </TableRow>
              ))}
            </tbody>
        </DataTable>
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-mutedText">{items.length} {t("rows")}</p>
          <Button type="button" variant="secondary" disabled={!issues.data?.next_cursor} onClick={() => setCursor(issues.data?.next_cursor ?? undefined)}>
            {t("nextPage")}
          </Button>
        </div>
      </section>
    </>
  );
}

function IssueCreate({ onBack, onCreated }: { onBack: () => void; onCreated: (id: string) => void }) {
  const { t, i18n } = useTranslation();
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const mutation = useMutation({ mutationFn: createIssue, onSuccess: (issue) => onCreated(issue.id) });
  const [form, setForm] = useState({ title: "", description: "", priority: "MEDIUM", primary_category_id: "", district_id: "", address: "" });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({ ...form, source: "portal", primary_category_id: form.primary_category_id || null, district_id: form.district_id || null });
  }

  return (
    <>
      <form onSubmit={submit} className="mx-auto grid max-w-3xl gap-4">
        <Button type="button" variant="muted" onClick={onBack} className="w-fit"><ArrowLeft size={18} />{t("back")}</Button>
        <Input placeholder={t("title")} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <Textarea placeholder={t("description")} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        <Select value={form.primary_category_id} onChange={(e) => setForm({ ...form, primary_category_id: e.target.value })}>
          <option value="">{t("category")}</option>
          {catalogs.data?.categories.map((category) => <option key={category.id} value={category.id}>{pickName(category, i18n.language)}</option>)}
        </Select>
        <Select value={form.district_id} onChange={(e) => setForm({ ...form, district_id: e.target.value })}>
          <option value="">{t("district")}</option>
          {catalogs.data?.districts.map((district) => <option key={district.id} value={district.id}>{pickName(district, i18n.language)}</option>)}
        </Select>
        <Input placeholder={t("address")} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        <Button disabled={mutation.isPending}><Send size={18} />{t("create")}</Button>
      </form>
    </>
  );
}

function IssueDetail({ issueId, role, onBack }: { issueId: string; role: RoleCode; onBack: () => void }) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const issue = useQuery({ queryKey: ["issue", issueId], queryFn: () => fetchIssue(issueId) });
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const [comment, setComment] = useState("");
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["issue", issueId] });
    queryClient.invalidateQueries({ queryKey: ["issues"] });
  };
  const transition = useMutation({ mutationFn: (status: string) => transitionIssue(issueId, status), onSuccess: invalidate });
  const qualify = useMutation({ mutationFn: () => qualifyIssue(issueId, { category_id: catalogs.data?.categories[0]?.id, priority: "HIGH", department_id: catalogs.data?.departments[0]?.id }), onSuccess: invalidate });
  const assign = useMutation({ mutationFn: () => assignIssue(issueId, { assigned_to_id: catalogs.data?.users.find((u: User) => u.role.code === "EXECUTOR")?.id, department_id: catalogs.data?.departments[0]?.id }), onSuccess: invalidate });
  const commentMutation = useMutation({ mutationFn: () => addIssueComment(issueId, comment), onSuccess: () => { setComment(""); invalidate(); } });
  const data = issue.data;

  return (
    <>
      <section className="mx-auto grid max-w-7xl gap-5 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-4">
          <Button type="button" variant="muted" onClick={onBack}><ArrowLeft size={18} />{t("back")}</Button>
          {data ? <IssueSummary issue={data} language={i18n.language} /> : null}
          <Card>
            <h2 className="mb-3 text-lg font-semibold">{t("photos")}</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              {data?.attachments?.map((attachment) => (
                <a key={attachment.id} href={attachment.file_url} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-md border border-border">
                  <img src={attachment.thumbnail_url ?? attachment.medium_url ?? attachment.file_url} className="h-36 w-full object-cover" />
                </a>
              ))}
            </div>
          </Card>
          <Card>
            <h2 className="mb-3 text-lg font-semibold">{t("timeline")}</h2>
            <div className="space-y-3">
              {data?.history?.map((entry) => <div key={entry.id} className="border-l-2 border-primary pl-3 text-sm"><b>{entry.action}</b> {entry.from_status ?? ""} {entry.to_status ? `-> ${entry.to_status}` : ""}<p className="text-foreground/60">{entry.actor?.full_name} · {new Date(entry.created_at).toLocaleString()}</p></div>)}
            </div>
          </Card>
        </div>
        <aside className="space-y-4">
          {data ? <SmartIssueCard issue={data} /> : null}
          <Actions role={role} issue={data} onQualify={() => qualify.mutate()} onAssign={() => assign.mutate()} onTransition={(status) => transition.mutate(status)} />
          <Card>
            <h2 className="mb-3 text-lg font-semibold">{t("comments")}</h2>
            <div className="mb-3 space-y-2">
              {data?.comments?.map((item) => <p key={item.id} className="rounded-md bg-muted p-2 text-sm">{item.content}</p>)}
            </div>
            <div className="flex gap-2">
              <Input className="min-w-0 flex-1" value={comment} onChange={(event) => setComment(event.target.value)} />
              <Button type="button" onClick={() => commentMutation.mutate()}><Send size={18} /></Button>
            </div>
          </Card>
        </aside>
      </section>
    </>
  );
}

function IssueSummary({ issue, language }: { issue: Issue; language: string }) {
  const { t } = useTranslation();
  return (
    <Card as="article" className="p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <StatusPill status={issue.status} isOverdue={issue.is_overdue} />
        <span className="rounded-chip bg-surface2 px-2.5 py-1 text-xs font-medium">{issue.priority}</span>
        <span className="rounded-chip bg-surface2 px-2.5 py-1 text-xs font-medium">{pickName(issue.category, language)}</span>
      </div>
      <h1 className="text-2xl font-semibold">{issue.title}</h1>
      <p className="mt-3 text-mutedText">{issue.description}</p>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <Meta label={t("address")} value={issue.address} />
        <Meta label={t("district")} value={pickName(issue.district, language)} />
        <Meta label={t("assignee")} value={issue.assigned_to?.full_name} />
        <Meta label={t("department")} value={pickName(issue.department, language)} />
        <Meta label={t("created")} value={new Date(issue.created_at).toLocaleString()} />
      </dl>
      <div className="mt-4 rounded-control border border-border bg-surface2 p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">{t("deadlines")}</h2>
          <span className={`rounded px-2 py-1 text-xs ${slaClass(issue)}`}>{slaText(issue, t("overdue")) || "-"}</span>
        </div>
        <dl className="grid gap-3 text-sm sm:grid-cols-3">
          <Meta label={t("reactionDue")} value={issue.reaction_due_at ? new Date(issue.reaction_due_at).toLocaleString() : ""} />
          <Meta label={t("executionDue")} value={issue.sla_due_at ? new Date(issue.sla_due_at).toLocaleString() : ""} />
          <Meta label={t("inspectionDue")} value={issue.inspection_due_at ? new Date(issue.inspection_due_at).toLocaleString() : ""} />
        </dl>
      </div>
    </Card>
  );
}

function Meta({ label, value }: { label: string; value?: string | null }) {
  return <div><dt className="text-mutedText">{label}</dt><dd className="font-medium">{value || ""}</dd></div>;
}

function SmartIssueCard({ issue }: { issue: Issue }) {
  const { t } = useTranslation();
  const risk = riskLevel(issue);
  const riskLabel = risk === "high" ? t("riskHigh") : risk === "medium" ? t("riskMedium") : t("riskLow");
  const riskClass =
    risk === "high"
      ? "bg-danger text-white"
      : risk === "medium"
        ? "bg-warning text-white"
        : "bg-primarySoft text-primary";
  return (
    <Card>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">{t("smartCard")}</h2>
          <p className="text-sm text-mutedText">{t("smartCardHint")}</p>
        </div>
        <span className={`rounded-chip px-2.5 py-1 text-xs font-medium ${riskClass}`}>{riskLabel}</span>
      </div>
      <div className="mt-5">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="text-mutedText">{t("progress")}</span>
          <span className="font-medium">{issueProgress(issue)}%</span>
        </div>
        <ProgressBar value={issueProgress(issue)} />
      </div>
      <div className="mt-5 grid gap-3 rounded-control bg-surface2 p-3 text-sm">
        <div>
          <p className="font-medium">{t("aiSummary")}</p>
          <p className="text-mutedText">{t("aiSummaryPlaceholder")}</p>
        </div>
        <div>
          <p className="font-medium">{t("aiForecast")}</p>
          <p className="text-mutedText">{t("aiForecastPlaceholder")}</p>
        </div>
      </div>
    </Card>
  );
}

function Actions({ role, issue, onQualify, onAssign, onTransition }: { role: RoleCode; issue?: Issue; onQualify: () => void; onAssign: () => void; onTransition: (status: string) => void }) {
  const { t } = useTranslation();
  if (!issue || role === "AKIM") return null;
  const actions = transitionActions(role, issue);
  const primary = actions.find((action) => action.primary) ?? actions[0];
  const secondary = actions.filter((action) => action !== primary);
  function run(action: { status: string; label: string }) {
    if (action.label === "qualify") onQualify();
    else if (action.label === "assign") onAssign();
    else onTransition(action.status);
  }
  return (
    <Card>
      <h2 className="mb-3 text-lg font-semibold">{t("actions")}</h2>
      {primary ? (
        <Button type="button" size="lg" className="w-full" onClick={() => run(primary)}>
          <Check size={18} />
          {t(primary.label)}
        </Button>
      ) : <p className="text-sm text-mutedText">{t("noActions")}</p>}
      {secondary.length ? (
        <div className="mt-3 grid gap-2">
          {secondary.map((action) => (
            <Button key={`${action.status}-${action.label}`} type="button" variant={action.label === "reject" ? "danger" : "secondary"} onClick={() => run(action)}>
              {action.label === "reject" ? <X size={18} /> : <ClipboardList size={18} />}
              {t(action.label)}
            </Button>
          ))}
        </div>
      ) : null}
    </Card>
  );
}

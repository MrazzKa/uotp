import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, ClipboardList, Download, Plus, Search, Send, Star, X } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
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
  setPersonalControl,
  submitIssue,
  transitionIssue,
  updateIssue
} from "../../lib/api";
import { useAuthStore } from "../../store/auth";
import type { CatalogItem, Issue, User } from "../../types";

type View = { name: "list" } | { name: "new" } | { name: "detail"; id: string };

const STATUSES = ["NEW", "ASSIGNED", "REVIEW_CONTROLLER", "REVIEW_AUTHOR", "CLOSED", "ON_HOLD"];
const IMPORTANCE = ["URGENT", "IMPORTANT", "NORMAL"];

function pickName(item: CatalogItem | null | undefined, language: string) {
  if (!item) return "";
  return language === "kk" ? item.name_kk : item.name_ru;
}

function impLabel(value: string) {
  return value === "URGENT" ? "Срочно" : value === "IMPORTANT" ? "Важно" : "Обычная";
}

function exportCsv(items: Issue[], t: (key: string) => string) {
  const header = ["Номер", "Статус", "Сфера", "Важность", "Срок", "Исполнитель", "Создана"];
  const rows = items.map((issue) => [
    issue.public_number,
    t(`st_${issue.status}`),
    issue.sphere?.name_ru ?? "",
    impLabel(issue.importance),
    issue.due_at ? new Date(issue.due_at).toLocaleString() : "",
    issue.assigned_to?.full_name ?? "",
    new Date(issue.created_at).toLocaleString()
  ]);
  const csv = [header, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(";"))
    .join("\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `uotp-tasks-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function dueText(issue: Issue, overdueLabel: string) {
  if (issue.is_overdue) return overdueLabel;
  if (!issue.due_at) return "";
  const minutes = Math.ceil((new Date(issue.due_at).getTime() - Date.now()) / 60000);
  if (minutes < 0) return overdueLabel;
  const hours = Math.floor(minutes / 60);
  if (hours >= 24) return `${Math.floor(hours / 24)}д`;
  const rest = minutes % 60;
  return hours > 0 ? `${hours}ч ${rest}м` : `${rest}м`;
}

function dueClass(issue: Issue) {
  if (issue.is_overdue) return "bg-danger text-white";
  if (!issue.due_at) return "bg-surface2 text-mutedText";
  const minutes = (new Date(issue.due_at).getTime() - Date.now()) / 60000;
  if (minutes <= 360) return "bg-warning text-white";
  return "bg-primarySoft text-primary";
}

const progressByStatus: Record<string, number> = {
  DRAFT: 5,
  NEW: 15,
  ASSIGNED: 40,
  REVIEW_CONTROLLER: 70,
  REVIEW_AUTHOR: 85,
  CLOSED: 100,
  ON_HOLD: 30
};

type TaskAction = { kind: "submit" | "transition" | "assign"; status?: string; label: string; primary?: boolean; danger?: boolean };

function taskActions(user: User, issue: Issue): TaskAction[] {
  const acts: TaskAction[] = [];
  const uid = user.id;
  const isAuthor = issue.created_by?.id === uid;
  const isController = issue.controller?.id === uid;
  const isExecutor = issue.assigned_to?.id === uid;
  const isAdmin = user.role.code === "ADMIN";
  if (isExecutor && issue.status === "ASSIGNED") {
    acts.push({ kind: "submit", label: "markDone", primary: true });
  }
  if (issue.status === "REVIEW_CONTROLLER" && (isController || isAuthor || isAdmin)) {
    acts.push({ kind: "transition", status: "CLOSED", label: "removeFromControl", primary: true });
    if (isController || isAdmin) acts.push({ kind: "transition", status: "REVIEW_AUTHOR", label: "toAuthor" });
    acts.push({ kind: "transition", status: "ASSIGNED", label: "notAccept", danger: true });
  }
  if (issue.status === "REVIEW_AUTHOR" && (isAuthor || isAdmin)) {
    acts.push({ kind: "transition", status: "CLOSED", label: "removeFromControl", primary: true });
    acts.push({ kind: "transition", status: "ASSIGNED", label: "notAccept", danger: true });
  }
  if (issue.status === "NEW" && (isAuthor || isAdmin || user.role.code === "OPERATOR")) {
    acts.push({ kind: "assign", label: "distribute", primary: true });
  }
  return acts;
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
      {view.name === "detail" ? <IssueDetail issueId={view.id} onBack={() => go({ name: "list" })} /> : null}
    </main>
  );
}

function IssueList({ onOpen, onNew }: { onOpen: (id: string) => void; onNew: () => void }) {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [importance, setImportance] = useState("");
  const [sphere, setSphere] = useState("");
  const [mode, setMode] = useState<"all" | "mine" | "personal" | "overdue" | "archive">("all");
  const [cursor, setCursor] = useState<string | undefined>();
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const params = useMemo(
    () => ({
      q: q || undefined,
      status: mode === "archive" ? "CLOSED" : status || undefined,
      importance: importance || undefined,
      sphere: sphere || undefined,
      is_overdue: mode === "overdue" ? "true" : undefined,
      personal: mode === "personal" ? "true" : undefined,
      assigned_to: mode === "mine" ? user?.id : undefined,
      cursor
    }),
    [q, status, importance, sphere, mode, user?.id, cursor]
  );
  const issues = useQuery({ queryKey: ["issues", params], queryFn: () => fetchIssues(params) });
  const items = issues.data?.items ?? [];

  return (
    <section className="mx-auto max-w-7xl">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 flex-wrap gap-2">
          <FilterChip active={mode === "all"} onClick={() => { setMode("all"); setCursor(undefined); }}>{t("all")}</FilterChip>
          <FilterChip active={mode === "mine"} onClick={() => { setMode("mine"); setCursor(undefined); }}>{t("mine")}</FilterChip>
          <FilterChip active={mode === "personal"} onClick={() => { setMode("personal"); setCursor(undefined); }}>{t("onlyPersonal")}</FilterChip>
          <FilterChip active={mode === "overdue"} onClick={() => { setMode("overdue"); setCursor(undefined); }}>{t("onlyOverdue")}</FilterChip>
          <FilterChip active={mode === "archive"} onClick={() => { setMode("archive"); setCursor(undefined); }}>{t("archive")}</FilterChip>
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-mutedText" />
            <Input className="pl-9" value={q} onChange={(event) => { setQ(event.target.value); setCursor(undefined); }} placeholder={t("search")} />
          </div>
          <Select value={status} onChange={(event) => { setStatus(event.target.value); setCursor(undefined); }}>
            <option value="">{t("status")}</option>
            {STATUSES.map((item) => <option key={item} value={item}>{t(`st_${item}`, item)}</option>)}
          </Select>
          <Select value={importance} onChange={(event) => { setImportance(event.target.value); setCursor(undefined); }}>
            <option value="">{t("importance")}</option>
            {IMPORTANCE.map((item) => <option key={item} value={item}>{impLabel(item)}</option>)}
          </Select>
          <Select value={sphere} onChange={(event) => { setSphere(event.target.value); setCursor(undefined); }}>
            <option value="">{t("sphere")}</option>
            {catalogs.data?.spheres.map((item) => <option key={item.id} value={item.id}>{pickName(item, i18n.language)}</option>)}
          </Select>
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="secondary" disabled={!items.length} onClick={() => exportCsv(items, t)}><Download size={18} />{t("export")}</Button>
          <Button onClick={onNew}><Plus size={18} />{t("newIssue")}</Button>
        </div>
      </div>
      <DataTable>
        <TableHead>
          <tr>
            <TableHeaderCell>{t("number")}</TableHeaderCell>
            {["status", "sphere", "importance", "sla", "assignee", "created"].map((key) => <TableHeaderCell key={key}>{t(key)}</TableHeaderCell>)}
          </tr>
        </TableHead>
        <tbody>
          {items.map((issue) => (
            <TableRow key={issue.id} className="cursor-pointer" onClick={() => onOpen(issue.id)}>
              <TableCell className="font-medium">{issue.public_number}</TableCell>
              <TableCell>
                <span className="inline-flex items-center gap-1.5">
                  <StatusPill status={issue.status} isOverdue={issue.is_overdue} />
                  {issue.on_personal_control ? <Star size={14} className="text-amber-500" fill="currentColor" /> : null}
                </span>
              </TableCell>
              <TableCell>{pickName(issue.sphere, i18n.language)}</TableCell>
              <TableCell>{impLabel(issue.importance)}</TableCell>
              <TableCell><span className={`rounded-chip px-2.5 py-1 text-xs font-medium ${dueClass(issue)}`}>{dueText(issue, t("overdue")) || "-"}</span></TableCell>
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
  );
}

function IssueCreate({ onBack, onCreated }: { onBack: () => void; onCreated: (id: string) => void }) {
  const { t, i18n } = useTranslation();
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const mutation = useMutation({ mutationFn: createIssue, onSuccess: (issue) => onCreated(issue.id) });
  const [form, setForm] = useState({ title: "", importance: "NORMAL", sphere_id: "", executor_id: "", address: "", due_at: "" });
  const [taskType, setTaskType] = useState("TASK");
  const [coExec, setCoExec] = useState<string[]>([]);
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(form.title), 500);
    return () => clearTimeout(timer);
  }, [form.title]);
  const similar = useQuery({
    queryKey: ["similar", debounced],
    queryFn: () => fetchIssues({ q: debounced, limit: "5" }),
    enabled: debounced.trim().length >= 5
  });
  const similarOpen = (similar.data?.items ?? []).filter((issue) => issue.status !== "CLOSED");

  function toggleCo(id: string) {
    setCoExec((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({
      source: "internal",
      task_type: taskType,
      title: form.title,
      importance: form.importance,
      sphere_id: form.sphere_id || undefined,
      executor_ids: form.executor_id ? [form.executor_id] : [],
      co_executor_ids: coExec.filter((id) => id !== form.executor_id),
      address: form.address || undefined,
      due_at: form.due_at ? new Date(form.due_at).toISOString() : undefined
    });
  }

  return (
    <form onSubmit={submit} className="mx-auto grid max-w-3xl gap-4">
      <Button type="button" variant="muted" onClick={onBack} className="w-fit"><ArrowLeft size={18} />{t("back")}</Button>
      <div className="flex gap-2">
        <FilterChip active={taskType === "TASK"} onClick={() => setTaskType("TASK")}>{t("typeTask")}</FilterChip>
        <FilterChip active={taskType === "EVENT"} onClick={() => setTaskType("EVENT")}>{t("typeEvent")}</FilterChip>
      </div>
      <Textarea placeholder={t("taskText")} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
      {similarOpen.length ? (
        <div className="rounded-control border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/30">
          <p className="mb-1 font-medium text-amber-800 dark:text-amber-200">{t("similarHint")}</p>
          <ul className="grid gap-1 text-amber-800/90 dark:text-amber-200/90">
            {similarOpen.slice(0, 3).map((issue) => <li key={issue.id}>{issue.public_number} · {issue.title}</li>)}
          </ul>
        </div>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <Select value={form.importance} onChange={(e) => setForm({ ...form, importance: e.target.value })}>
          {IMPORTANCE.map((item) => <option key={item} value={item}>{impLabel(item)}</option>)}
        </Select>
        <Select value={form.sphere_id} onChange={(e) => setForm({ ...form, sphere_id: e.target.value })}>
          <option value="">{t("sphere")}</option>
          {catalogs.data?.spheres.map((item) => <option key={item.id} value={item.id}>{pickName(item, i18n.language)}</option>)}
        </Select>
        <Select value={form.executor_id} onChange={(e) => setForm({ ...form, executor_id: e.target.value })}>
          <option value="">{t("assignee")}</option>
          {catalogs.data?.users.map((u: User) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
        </Select>
        <Input type="datetime-local" value={form.due_at} onChange={(e) => setForm({ ...form, due_at: e.target.value })} />
      </div>
      <Input placeholder={t("address")} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
      <div>
        <p className="mb-2 text-sm text-mutedText">{t("coExecutors")}</p>
        <div className="flex flex-wrap gap-2">
          {catalogs.data?.users
            .filter((u: User) => u.id !== form.executor_id)
            .map((u: User) => (
              <FilterChip key={u.id} active={coExec.includes(u.id)} onClick={() => toggleCo(u.id)}>{u.full_name}</FilterChip>
            ))}
        </div>
      </div>
      <Button disabled={mutation.isPending || form.title.length < 3}><Send size={18} />{t("create")}</Button>
    </form>
  );
}

function IssueDetail({ issueId, onBack }: { issueId: string; onBack: () => void }) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const issue = useQuery({ queryKey: ["issue", issueId], queryFn: () => fetchIssue(issueId) });
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const [comment, setComment] = useState("");
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["issue", issueId] });
    queryClient.invalidateQueries({ queryKey: ["issues"] });
  };
  const transition = useMutation({ mutationFn: (status: string) => transitionIssue(issueId, status), onSuccess: invalidate });
  const submit = useMutation({ mutationFn: (report?: string) => submitIssue(issueId, report), onSuccess: invalidate });
  const update = useMutation({ mutationFn: (payload: Record<string, unknown>) => updateIssue(issueId, payload), onSuccess: invalidate });
  const assign = useMutation({ mutationFn: (executorId: string) => assignIssue(issueId, { executor_ids: [executorId] }), onSuccess: invalidate });
  const personal = useMutation({
    mutationFn: (on: boolean) => setPersonalControl(issueId, on, issue.data?.importance ?? "NORMAL"),
    onSuccess: invalidate
  });
  const commentMutation = useMutation({ mutationFn: () => addIssueComment(issueId, comment), onSuccess: () => { setComment(""); invalidate(); } });
  const data = issue.data;

  return (
    <section className="mx-auto grid max-w-7xl gap-5 lg:grid-cols-[1.5fr_1fr]">
      <div className="space-y-4">
        <Button type="button" variant="muted" onClick={onBack}><ArrowLeft size={18} />{t("back")}</Button>
        {data ? <IssueSummary issue={data} language={i18n.language} /> : null}
        {data?.attachments?.length ? (
          <Card>
            <h2 className="mb-3 text-lg font-semibold">{t("photos")}</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              {data.attachments.map((attachment) => (
                <a key={attachment.id} href={attachment.file_url} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-md border border-border">
                  <img src={attachment.thumbnail_url ?? attachment.medium_url ?? attachment.file_url} className="h-36 w-full object-cover" />
                </a>
              ))}
            </div>
          </Card>
        ) : null}
        <Card>
          <h2 className="mb-3 text-lg font-semibold">{t("timeline")}</h2>
          <div className="space-y-3">
            {data?.history?.map((entry) => (
              <div key={entry.id} className="border-l-2 border-primary pl-3 text-sm">
                <b>{t(`ev_${entry.action}`, entry.action)}</b> {entry.to_status ? `→ ${t(`st_${entry.to_status}`, entry.to_status)}` : ""}
                <p className="text-foreground/60">{entry.actor?.full_name} · {new Date(entry.created_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <aside className="space-y-4">
        {data && user ? (
          <Actions
            issue={data}
            user={user}
            users={catalogs.data?.users ?? []}
            onSubmit={(report) => submit.mutate(report)}
            onAssign={(executorId) => assign.mutate(executorId)}
            onTransition={(status) => transition.mutate(status)}
            onTogglePersonal={() => personal.mutate(!data.on_personal_control)}
          />
        ) : null}
        {data && user && data.created_by?.id === user.id && ["DRAFT", "NEW", "ASSIGNED"].includes(data.status) ? (
          <EditPanel issue={data} spheres={catalogs.data?.spheres ?? []} onSave={(payload) => update.mutate(payload)} />
        ) : null}
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
  );
}

function IssueSummary({ issue, language }: { issue: Issue; language: string }) {
  const { t } = useTranslation();
  return (
    <Card as="article" className="p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <StatusPill status={issue.status} isOverdue={issue.is_overdue} />
        <span className="rounded-chip bg-surface2 px-2.5 py-1 text-xs font-medium">{impLabel(issue.importance)}</span>
        {issue.sphere ? <span className="rounded-chip bg-surface2 px-2.5 py-1 text-xs font-medium">{pickName(issue.sphere, language)}</span> : null}
        {issue.on_personal_control ? (
          <span className="inline-flex items-center gap-1 rounded-chip bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700"><Star size={12} fill="currentColor" />{t("onlyPersonal")}</span>
        ) : null}
      </div>
      <h1 className="text-xl font-semibold">{issue.title}</h1>
      {issue.description && issue.description !== issue.title ? <p className="mt-3 text-mutedText">{issue.description}</p> : null}
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <Meta label={t("assignee")} value={issue.assigned_to?.full_name} />
        <Meta label={t("controller")} value={issue.controller?.full_name} />
        <Meta label={t("address")} value={issue.address} />
        <Meta label={t("created")} value={new Date(issue.created_at).toLocaleString()} />
      </dl>
      <div className="mt-4 rounded-control border border-border bg-surface2 p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">{t("dueDate")}</h2>
          <span className={`rounded px-2 py-1 text-xs ${dueClass(issue)}`}>{dueText(issue, t("overdue")) || "-"}</span>
        </div>
        <p className="text-sm text-mutedText">{issue.due_at ? new Date(issue.due_at).toLocaleString() : "-"}</p>
        <ProgressBar value={progressByStatus[issue.status] ?? 0} className="mt-3" />
      </div>
    </Card>
  );
}

function Meta({ label, value }: { label: string; value?: string | null }) {
  return <div><dt className="text-mutedText">{label}</dt><dd className="font-medium">{value || "-"}</dd></div>;
}

function Actions({
  issue,
  user,
  users,
  onSubmit,
  onAssign,
  onTransition,
  onTogglePersonal
}: {
  issue: Issue;
  user: User;
  users: User[];
  onSubmit: (report?: string) => void;
  onAssign: (executorId: string) => void;
  onTransition: (status: string) => void;
  onTogglePersonal: () => void;
}) {
  const { t } = useTranslation();
  const [executor, setExecutor] = useState("");
  const [report, setReport] = useState("");
  const actions = taskActions(user, issue);
  const primary = actions.find((action) => action.primary) ?? actions[0];
  const secondary = actions.filter((action) => action !== primary);
  const hasSubmit = actions.some((action) => action.kind === "submit");

  function run(action: TaskAction) {
    if (action.kind === "submit") onSubmit(report || undefined);
    else if (action.kind === "assign") { if (executor) onAssign(executor); }
    else if (action.status) onTransition(action.status);
  }

  return (
    <Card>
      <h2 className="mb-3 text-lg font-semibold">{t("actions")}</h2>
      {hasSubmit ? (
        <div className="mb-3">
          <p className="mb-1 text-sm text-mutedText">{t("report")}</p>
          <Textarea placeholder={t("reportHint")} value={report} onChange={(e) => setReport(e.target.value)} />
        </div>
      ) : null}
      {primary?.kind === "assign" ? (
        <div className="mb-3 grid gap-2">
          <Select value={executor} onChange={(e) => setExecutor(e.target.value)}>
            <option value="">{t("assignee")}</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
          </Select>
        </div>
      ) : null}
      {primary ? (
        <Button type="button" size="lg" className="w-full" disabled={primary.kind === "assign" && !executor} onClick={() => run(primary)}>
          <Check size={18} />{t(primary.label)}
        </Button>
      ) : <p className="text-sm text-mutedText">{t("noActions")}</p>}
      {secondary.length ? (
        <div className="mt-3 grid gap-2">
          {secondary.map((action) => (
            <Button key={`${action.kind}-${action.status}-${action.label}`} type="button" variant={action.danger ? "danger" : "secondary"} onClick={() => run(action)}>
              {action.danger ? <X size={18} /> : <ClipboardList size={18} />}{t(action.label)}
            </Button>
          ))}
        </div>
      ) : null}
      <div className="mt-3 border-t border-border pt-3">
        <Button type="button" variant={issue.on_personal_control ? "danger" : "secondary"} className="w-full" onClick={onTogglePersonal}>
          <Star size={18} fill={issue.on_personal_control ? "currentColor" : "none"} />
          {t(issue.on_personal_control ? "personalControlOff" : "personalControlOn")}
        </Button>
      </div>
    </Card>
  );
}

function EditPanel({ issue, spheres, onSave }: { issue: Issue; spheres: CatalogItem[]; onSave: (payload: Record<string, unknown>) => void }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(issue.title);
  const [importance, setImportance] = useState(issue.importance);
  const [sphereId, setSphereId] = useState(issue.sphere?.id ?? "");
  const [dueAt, setDueAt] = useState(issue.due_at ? new Date(issue.due_at).toISOString().slice(0, 16) : "");

  if (!open) {
    return <Button type="button" variant="secondary" className="w-full" onClick={() => setOpen(true)}>{t("edit")}</Button>;
  }
  return (
    <Card>
      <h2 className="mb-3 text-lg font-semibold">{t("edit")}</h2>
      <div className="grid gap-3">
        <Textarea value={title} onChange={(e) => setTitle(e.target.value)} />
        <Select value={importance} onChange={(e) => setImportance(e.target.value)}>
          {IMPORTANCE.map((item) => <option key={item} value={item}>{impLabel(item)}</option>)}
        </Select>
        <Select value={sphereId} onChange={(e) => setSphereId(e.target.value)}>
          <option value="">{t("sphere")}</option>
          {spheres.map((s) => <option key={s.id} value={s.id}>{pickName(s, i18n.language)}</option>)}
        </Select>
        <Input type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
        <div className="flex gap-2">
          <Button
            type="button"
            onClick={() => {
              onSave({
                title,
                importance,
                sphere_id: sphereId || undefined,
                due_at: dueAt ? new Date(dueAt).toISOString() : undefined
              });
              setOpen(false);
            }}
          >
            {t("save")}
          </Button>
          <Button type="button" variant="secondary" onClick={() => setOpen(false)}>{t("back")}</Button>
        </div>
      </div>
    </Card>
  );
}

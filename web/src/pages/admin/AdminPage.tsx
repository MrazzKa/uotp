import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input, Select } from "../../components/ui/Field";
import { FilterChip } from "../../components/ui/FilterChip";
import { DataTable, TableCell, TableHead, TableHeaderCell, TableRow } from "../../components/ui/Table";
import {
  createDepartment,
  createSphere,
  createUser,
  deleteDepartment,
  deleteSphere,
  fetchCatalogs,
  fetchRoles,
  updateUser
} from "../../lib/api";
import type { CatalogItem, Role, User } from "../../types";

type Tab = "spheres" | "departments" | "users";

const DEPARTMENT_TYPES = ["apparatus", "apparat_dept", "district_dept", "rural_okrug", "contractor"];

function deptTypeLabel(type: string) {
  return type === "apparatus"
    ? "Аппарат"
    : type === "apparat_dept"
      ? "Отдел аппарата"
      : type === "district_dept"
        ? "Районный отдел"
        : type === "rural_okrug"
          ? "Сельский округ"
          : type === "contractor"
            ? "Подрядная организация"
            : type;
}

export function AdminPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("spheres");
  return (
    <main className="mx-auto max-w-6xl">
      <h1 className="mb-4 text-2xl font-semibold">{t("adminTitle")}</h1>
      <div className="mb-5 flex flex-wrap gap-2">
        <FilterChip active={tab === "spheres"} onClick={() => setTab("spheres")}>{t("spheresTab")}</FilterChip>
        <FilterChip active={tab === "departments"} onClick={() => setTab("departments")}>{t("departmentsTab")}</FilterChip>
        <FilterChip active={tab === "users"} onClick={() => setTab("users")}>{t("usersTab")}</FilterChip>
      </div>
      {tab === "spheres" ? <SpheresAdmin /> : null}
      {tab === "departments" ? <DepartmentsAdmin /> : null}
      {tab === "users" ? <UsersAdmin /> : null}
    </main>
  );
}

function SpheresAdmin() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["catalogs"] });
  const create = useMutation({ mutationFn: createSphere, onSuccess: invalidate });
  const remove = useMutation({ mutationFn: deleteSphere, onSuccess: invalidate });
  const [form, setForm] = useState({ code: "", name_ru: "", name_kk: "", color: "#2563eb" });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate({ ...form, name_kk: form.name_kk || form.name_ru }, { onSuccess: () => setForm({ code: "", name_ru: "", name_kk: "", color: "#2563eb" }) });
  }

  return (
    <div className="grid gap-4">
      <Card as="form" onSubmit={submit} className="grid gap-3 sm:grid-cols-[1fr_2fr_2fr_auto_auto] sm:items-end">
        <Field label={t("code")}><Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></Field>
        <Field label={t("nameRu")}><Input value={form.name_ru} onChange={(e) => setForm({ ...form, name_ru: e.target.value })} /></Field>
        <Field label={t("nameKk")}><Input value={form.name_kk} onChange={(e) => setForm({ ...form, name_kk: e.target.value })} /></Field>
        <Field label={t("color")}><input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} className="h-10 w-14 rounded-control border border-border" /></Field>
        <Button disabled={create.isPending || form.code.length < 2 || form.name_ru.length < 2}><Plus size={18} />{t("add")}</Button>
      </Card>
      <DataTable>
        <TableHead>
          <tr>{["code", "nameRu", "nameKk", ""].map((key, i) => <TableHeaderCell key={i}>{key ? t(key) : ""}</TableHeaderCell>)}</tr>
        </TableHead>
        <tbody>
          {catalogs.data?.spheres.map((sphere: CatalogItem) => (
            <TableRow key={sphere.id}>
              <TableCell>
                <span className="inline-flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ background: sphere.color ?? "#94a3b8" }} />
                  {sphere.code}
                </span>
              </TableCell>
              <TableCell>{sphere.name_ru}</TableCell>
              <TableCell>{sphere.name_kk}</TableCell>
              <TableCell><IconDelete onClick={() => remove.mutate(sphere.id)} /></TableCell>
            </TableRow>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
}

function DepartmentsAdmin() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["catalogs"] });
  const create = useMutation({ mutationFn: createDepartment, onSuccess: invalidate });
  const remove = useMutation({ mutationFn: deleteDepartment, onSuccess: invalidate });
  const [form, setForm] = useState({ name_ru: "", name_kk: "", type: "district_dept" });

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate({ ...form, name_kk: form.name_kk || form.name_ru }, { onSuccess: () => setForm({ name_ru: "", name_kk: "", type: "district_dept" }) });
  }

  return (
    <div className="grid gap-4">
      <Card as="form" onSubmit={submit} className="grid gap-3 sm:grid-cols-[2fr_2fr_2fr_auto] sm:items-end">
        <Field label={t("nameRu")}><Input value={form.name_ru} onChange={(e) => setForm({ ...form, name_ru: e.target.value })} /></Field>
        <Field label={t("nameKk")}><Input value={form.name_kk} onChange={(e) => setForm({ ...form, name_kk: e.target.value })} /></Field>
        <Field label={t("orgType")}>
          <Select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            {DEPARTMENT_TYPES.map((type) => <option key={type} value={type}>{deptTypeLabel(type)}</option>)}
          </Select>
        </Field>
        <Button disabled={create.isPending || form.name_ru.length < 2}><Plus size={18} />{t("add")}</Button>
      </Card>
      <DataTable>
        <TableHead>
          <tr>{["nameRu", "orgType", ""].map((key, i) => <TableHeaderCell key={i}>{key ? t(key) : ""}</TableHeaderCell>)}</tr>
        </TableHead>
        <tbody>
          {catalogs.data?.departments.map((dept: CatalogItem) => (
            <TableRow key={dept.id}>
              <TableCell>{dept.name_ru}</TableCell>
              <TableCell>{deptTypeLabel(dept.type ?? "")}</TableCell>
              <TableCell><IconDelete onClick={() => remove.mutate(dept.id)} /></TableCell>
            </TableRow>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
}

function UsersAdmin() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const catalogs = useQuery({ queryKey: ["catalogs"], queryFn: fetchCatalogs });
  const roles = useQuery({ queryKey: ["roles"], queryFn: fetchRoles });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["catalogs"] });
  const create = useMutation({ mutationFn: createUser, onSuccess: invalidate });
  const patch = useMutation({ mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => updateUser(id, payload), onSuccess: invalidate });
  const empty = { full_name: "", email: "", role_id: "", sphere_id: "", department_id: "", position_title: "" };
  const [form, setForm] = useState(empty);

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate(
      {
        full_name: form.full_name,
        email: form.email,
        role_id: form.role_id,
        sphere_id: form.sphere_id || undefined,
        department_id: form.department_id || undefined,
        position_title: form.position_title || undefined
      },
      { onSuccess: () => setForm(empty) }
    );
  }

  return (
    <div className="grid gap-4">
      <Card as="form" onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <Field label={t("fullName")}><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
        <Field label="Email"><Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
        <Field label={t("role")}>
          <Select value={form.role_id} onChange={(e) => setForm({ ...form, role_id: e.target.value })}>
            <option value="">{t("role")}</option>
            {roles.data?.map((role: Role) => <option key={role.id} value={role.id}>{role.name_ru}</option>)}
          </Select>
        </Field>
        <Field label={t("position")}><Input value={form.position_title} onChange={(e) => setForm({ ...form, position_title: e.target.value })} /></Field>
        <Field label={t("sphere")}>
          <Select value={form.sphere_id} onChange={(e) => setForm({ ...form, sphere_id: e.target.value })}>
            <option value="">{t("sphere")}</option>
            {catalogs.data?.spheres.map((s: CatalogItem) => <option key={s.id} value={s.id}>{s.name_ru}</option>)}
          </Select>
        </Field>
        <Field label={t("department")}>
          <Select value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
            <option value="">{t("department")}</option>
            {catalogs.data?.departments.map((d: CatalogItem) => <option key={d.id} value={d.id}>{d.name_ru}</option>)}
          </Select>
        </Field>
        <div className="sm:col-span-2">
          <Button disabled={create.isPending || form.full_name.length < 2 || !form.email || !form.role_id}><Plus size={18} />{t("add")}</Button>
        </div>
      </Card>
      <DataTable>
        <TableHead>
          <tr>{["fullName", "email", "position", "role"].map((key) => <TableHeaderCell key={key}>{key === "email" ? "Email" : t(key)}</TableHeaderCell>)}</tr>
        </TableHead>
        <tbody>
          {catalogs.data?.users.map((user: User) => (
            <TableRow key={user.id}>
              <TableCell className="font-medium">{user.full_name}</TableCell>
              <TableCell>{user.email}</TableCell>
              <TableCell>
                <Input
                  className="min-w-[180px]"
                  defaultValue={user.position_title ?? ""}
                  onBlur={(e) => {
                    if (e.target.value !== (user.position_title ?? "")) patch.mutate({ id: user.id, payload: { position_title: e.target.value } });
                  }}
                />
              </TableCell>
              <TableCell>
                <Select
                  value={user.role.id}
                  onChange={(e) => patch.mutate({ id: user.id, payload: { role_id: e.target.value } })}
                  className="min-w-[160px]"
                >
                  {roles.data?.map((role: Role) => <option key={role.id} value={role.id}>{role.name_ru}</option>)}
                </Select>
              </TableCell>
            </TableRow>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-mutedText">{label}</span>
      {children}
    </label>
  );
}

function IconDelete({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="rounded-control p-2 text-mutedText transition hover:bg-danger/10 hover:text-danger">
      <Trash2 size={16} />
    </button>
  );
}

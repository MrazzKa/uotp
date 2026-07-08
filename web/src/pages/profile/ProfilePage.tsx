import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Input } from "../../components/ui/Field";
import { changePassword } from "../../lib/api";
import { useAuthStore } from "../../store/auth";

export function ProfilePage() {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [done, setDone] = useState(false);
  const mutation = useMutation({
    mutationFn: () => changePassword(current, next),
    onSuccess: () => {
      setDone(true);
      setCurrent("");
      setNext("");
    }
  });

  if (!user) return null;
  const roleName = i18n.language === "kk" ? user.role.name_kk : user.role.name_ru;

  return (
    <main className="mx-auto grid max-w-2xl gap-4">
      <h1 className="text-2xl font-semibold">{t("profileTab")}</h1>
      <Card className="grid gap-1">
        <p className="text-lg font-semibold">{user.full_name}</p>
        <p className="text-sm text-mutedText">{roleName}{user.position_title ? ` · ${user.position_title}` : ""}</p>
        <p className="text-sm text-mutedText">{user.email}</p>
        <p className="text-sm text-mutedText">{user.tenant.name_ru}</p>
      </Card>
      <Card>
        <h2 className="mb-3 text-lg font-semibold">{t("changePassword")}</h2>
        <div className="grid gap-3">
          <Input type="password" placeholder={t("currentPassword")} value={current} onChange={(e) => { setCurrent(e.target.value); setDone(false); }} />
          <Input type="password" placeholder={t("newPassword")} value={next} onChange={(e) => { setNext(e.target.value); setDone(false); }} />
          <div>
            <Button type="button" disabled={mutation.isPending || current.length < 1 || next.length < 6} onClick={() => mutation.mutate()}>{t("save")}</Button>
          </div>
          {mutation.isError ? <p className="text-sm text-danger">{t("passwordError")}</p> : null}
          {done ? <p className="text-sm text-success">{t("passwordChanged")}</p> : null}
        </div>
      </Card>
    </main>
  );
}

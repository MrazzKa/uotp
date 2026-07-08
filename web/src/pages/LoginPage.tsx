import { useMutation } from "@tanstack/react-query";
import { LockKeyhole, LogIn } from "lucide-react";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Field";
import { fetchMe, login } from "../lib/api";

const DEMO_ACCOUNTS = [
  { label: "Аким района", email: "akim@uotp.local" },
  { label: "Рук. аппарата", email: "apparat@uotp.local" },
  { label: "Оператор", email: "operator@uotp.local" },
  { label: "Рук. отдела ЖКХ", email: "head_gkh@uotp.local" },
  { label: "Специалист", email: "spec_gkh@uotp.local" },
  { label: "Аким с/о", email: "so_beskol@uotp.local" },
  { label: "Подрядчик", email: "con_clean@uotp.local" },
  { label: "Админ", email: "admin@uotp.local" }
];

export function LoginPage() {
  const { t } = useTranslation();
  const [identifier, setIdentifier] = useState("akim@uotp.local");
  const [password, setPassword] = useState("demo123");
  const mutation = useMutation({
    mutationFn: async () => {
      await login(identifier, password);
      return fetchMe();
    }
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <main className="grid min-h-screen place-items-center px-4">
      <Card as="form" onSubmit={onSubmit} className="w-full max-w-sm p-6">
        <div className="mb-6 flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-control bg-primarySoft text-primary">
            <LockKeyhole size={20} />
          </div>
          <h1 className="text-xl font-semibold">UOTP</h1>
        </div>
        <label className="mb-3 block text-sm">
          <span className="mb-1 block">{t("identifier")}</span>
          <Input value={identifier} onChange={(event) => setIdentifier(event.target.value)} />
        </label>
        <label className="mb-5 block text-sm">
          <span className="mb-1 block">{t("password")}</span>
          <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        <Button type="submit" disabled={mutation.isPending} className="w-full">
          <LogIn size={18} />
          {t("signIn")}
        </Button>
        {mutation.isError ? <p className="mt-3 text-sm text-red-500">{t("loginFailed")}</p> : null}
        <div className="mt-5 border-t border-border pt-4">
          <p className="mb-2 text-xs text-mutedText">Демо-вход (пароль demo123)</p>
          <div className="flex flex-wrap gap-1.5">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                onClick={() => setIdentifier(account.email)}
                className={`rounded-chip border px-2.5 py-1 text-xs transition ${
                  identifier === account.email ? "border-primary bg-primarySoft text-primary" : "border-border text-mutedText hover:bg-surface2"
                }`}
              >
                {account.label}
              </button>
            ))}
          </div>
        </div>
      </Card>
    </main>
  );
}

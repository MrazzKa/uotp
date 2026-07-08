import { useMutation } from "@tanstack/react-query";
import { LockKeyhole, LogIn } from "lucide-react";
import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Field";
import { fetchMe, login } from "../lib/api";

export function LoginPage() {
  const { t } = useTranslation();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
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
          <Input value={identifier} autoComplete="username" onChange={(event) => setIdentifier(event.target.value)} />
        </label>
        <label className="mb-5 block text-sm">
          <span className="mb-1 block">{t("password")}</span>
          <Input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        <Button type="submit" disabled={mutation.isPending || !identifier || !password} className="w-full">
          <LogIn size={18} />
          {t("signIn")}
        </Button>
        {mutation.isError ? <p className="mt-3 text-sm text-red-500">{t("loginFailed")}</p> : null}
      </Card>
    </main>
  );
}

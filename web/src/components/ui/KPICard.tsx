import { LucideIcon } from "lucide-react";

import { Card } from "./Card";

type Tone = "primary" | "danger" | "warning" | "success" | "info";

const toneClasses: Record<Tone, string> = {
  primary: "bg-primarySoft text-primary",
  danger: "bg-red-50 text-danger dark:bg-red-950/35",
  warning: "bg-amber-50 text-warning dark:bg-amber-950/35",
  success: "bg-emerald-50 text-success dark:bg-emerald-950/35",
  info: "bg-blue-50 text-info dark:bg-blue-950/35"
};

export function KPICard({
  label,
  value,
  hint,
  tone = "primary",
  icon: Icon
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: Tone;
  icon?: LucideIcon;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm text-mutedText">{label}</p>
          <p className="mt-2 text-[32px] font-semibold leading-none tracking-tight text-foreground">{value}</p>
          {hint ? <p className="mt-2 text-xs text-mutedText">{hint}</p> : null}
        </div>
        {Icon ? (
          <div className={`grid h-10 w-10 shrink-0 place-items-center rounded-control ${toneClasses[tone]}`}>
            <Icon className="h-5 w-5 stroke-[1.6]" />
          </div>
        ) : null}
      </div>
    </Card>
  );
}

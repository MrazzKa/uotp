import { ArrowDownRight, ArrowUpRight, LucideIcon } from "lucide-react";

import { Card } from "./Card";

export function KPICard({
  label,
  value,
  delta,
  trend = "up",
  icon: Icon
}: {
  label: string;
  value: string | number;
  delta?: string;
  trend?: "up" | "down";
  icon?: LucideIcon;
}) {
  const TrendIcon = trend === "up" ? ArrowUpRight : ArrowDownRight;
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-mutedText">{label}</p>
          <p className="mt-2 text-[28px] font-semibold leading-none tracking-normal text-foreground">
            {value}
          </p>
        </div>
        {Icon ? (
          <div className="grid h-10 w-10 place-items-center rounded-control bg-primarySoft text-primary">
            <Icon className="h-5 w-5 stroke-[1.6]" />
          </div>
        ) : null}
      </div>
      {delta ? (
        <span
          className={`mt-4 inline-flex items-center gap-1 rounded-chip px-2.5 py-1 text-xs font-medium ${
            trend === "up"
              ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/35 dark:text-emerald-200"
              : "bg-red-50 text-red-700 dark:bg-red-950/35 dark:text-red-200"
          }`}
        >
          <TrendIcon className="h-3.5 w-3.5 stroke-[1.7]" />
          {delta}
        </span>
      ) : null}
    </Card>
  );
}

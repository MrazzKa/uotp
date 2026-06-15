import { HTMLAttributes } from "react";
import { useTranslation } from "react-i18next";

import { statusColor, statusLabelKey } from "../../lib/design";
import { cn } from "../../lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-chip px-2.5 py-1 text-xs font-medium",
        className
      )}
      {...props}
    />
  );
}

export function StatusPill({
  status,
  isOverdue,
  className
}: {
  status: string;
  isOverdue?: boolean;
  className?: string;
}) {
  const { t } = useTranslation();
  const colors = statusColor(status, isOverdue);
  return (
    <Badge className={cn(colors.bg, colors.text, className)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", colors.dot)} />
      {t(statusLabelKey(status), status)}
    </Badge>
  );
}

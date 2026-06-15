import { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function FilterChip({
  active,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      className={cn(
        "h-9 rounded-chip border px-3 text-sm font-medium transition",
        active
          ? "border-primary bg-primarySoft text-primary"
          : "border-border bg-surface text-mutedText hover:bg-surface2 hover:text-foreground",
        className
      )}
      type="button"
      {...props}
    />
  );
}

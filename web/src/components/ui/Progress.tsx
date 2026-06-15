import { cn } from "../../lib/utils";

export function ProgressBar({ value, className }: { value: number; className?: string }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("h-2 overflow-hidden rounded-chip bg-surface2", className)}>
      <div className="h-full rounded-chip bg-primary transition-all" style={{ width: `${clamped}%` }} />
    </div>
  );
}

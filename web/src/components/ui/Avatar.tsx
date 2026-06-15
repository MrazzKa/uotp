import { cn } from "../../lib/utils";

export function AvatarInitials({ name, className }: { name?: string | null; className?: string }) {
  const initials =
    name
      ?.split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase() || "U";
  return (
    <span
      className={cn(
        "inline-grid h-8 w-8 shrink-0 place-items-center rounded-chip bg-primarySoft text-xs font-semibold text-primary",
        className
      )}
    >
      {initials}
    </span>
  );
}

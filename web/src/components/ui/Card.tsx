import { ElementType, HTMLAttributes } from "react";

import { cn } from "../../lib/utils";

type CardProps = HTMLAttributes<HTMLElement> & {
  as?: ElementType;
};

export function Card({ as: Component = "div", className, ...props }: CardProps) {
  return (
    <Component
      className={cn("rounded-panel border border-border bg-surface p-5 shadow-card", className)}
      {...props}
    />
  );
}

export function Panel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <section
      className={cn("rounded-panel border border-border bg-surface p-5 shadow-card", className)}
      {...props}
    />
  );
}

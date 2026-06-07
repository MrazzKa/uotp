import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium transition hover:opacity-90 disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-white",
        muted: "bg-muted text-foreground",
        accent: "bg-accent text-foreground"
      }
    },
    defaultVariants: {
      variant: "default"
    }
  }
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  };

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ asChild = false, className, variant, ...props }, ref) => {
    const Component = asChild ? Slot : "button";
    return <Component ref={ref} className={cn(buttonVariants({ variant }), className)} {...props} />;
  }
);

Button.displayName = "Button";

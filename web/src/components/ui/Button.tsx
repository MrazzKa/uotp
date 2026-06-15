import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-control text-sm font-medium transition duration-150 disabled:pointer-events-none disabled:opacity-50 [&_svg]:h-4 [&_svg]:w-4 [&_svg]:stroke-[1.7]",
  {
    variants: {
      variant: {
        default: "bg-primary text-white shadow-base hover:bg-primaryHover",
        secondary: "border border-border bg-surface text-foreground shadow-base hover:bg-surface2",
        muted: "bg-surface2 text-foreground hover:bg-primarySoft",
        accent: "bg-primarySoft text-primary hover:bg-surface2",
        ghost: "bg-transparent text-mutedText hover:bg-surface2 hover:text-foreground",
        danger: "bg-danger text-white shadow-base hover:opacity-90"
      },
      size: {
        sm: "h-8 px-3 text-[13px]",
        md: "h-10 px-4",
        lg: "h-11 px-5",
        icon: "h-10 w-10 px-0"
      }
    },
    defaultVariants: {
      variant: "default",
      size: "md"
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

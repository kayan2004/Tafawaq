import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "bordered" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  children: ReactNode;
}

const base = "inline-flex items-center justify-center gap-1.5 rounded-md text-[13px] font-bold transition-opacity duration-150 disabled:opacity-45 disabled:cursor-not-allowed";

const variants: Record<Variant, string> = {
  primary: "h-[34px] px-3.5 bg-[#262d39] text-white",
  bordered: "h-[34px] px-3 bg-[var(--surface)] text-[var(--text)] border border-[var(--line-strong)]",
  ghost: "h-auto px-0 bg-transparent text-[var(--text-2)] font-semibold",
  danger: "h-auto px-2.5 py-1 text-[var(--danger)] border border-[var(--danger-line)] rounded-[5px] text-xs",
};

export default function Button({ variant = "bordered", className = "", children, ...rest }: ButtonProps) {
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...rest}>
      {children}
    </button>
  );
}

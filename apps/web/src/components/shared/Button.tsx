/**
 * 通用按钮组件 - 对标 HTML Demo 的 button 样式
 */
import { clsx } from "clsx";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "default" | "small" | "small-primary" | "small-ghost" | "small-danger";
  children: React.ReactNode;
}

export function Button({ variant = "default", children, className, ...props }: ButtonProps) {
  const base = "border rounded-lg font-bold whitespace-nowrap cursor-pointer";
  const variants: Record<string, string> = {
    default: "border-[#d8dee6] bg-white text-[#1d2939] px-3 py-2",
    primary: "bg-[#23675f] border-[#23675f] text-white px-3 py-2",
    ghost: "bg-transparent border-[#d8dee6] text-[#1d2939] px-3 py-2",
    small: "border-[#d8dee6] bg-white text-[#1d2939] px-2 py-1.5 text-xs",
    "small-primary": "bg-[#23675f] border-[#23675f] text-white px-2 py-1.5 text-xs",
    "small-ghost": "bg-transparent border-[#d8dee6] text-[#1d2939] px-2 py-1.5 text-xs",
    "small-danger": "bg-[#dc2626] border-[#dc2626] text-white px-2 py-1.5 text-xs",
  };

  return (
    <button
      className={clsx(base, variants[variant], className)}
      {...props}
    >
      {children}
    </button>
  );
}

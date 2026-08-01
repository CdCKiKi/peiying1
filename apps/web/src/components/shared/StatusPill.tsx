/**
 * 状态徽章 - 对标 HTML Demo 的 pill 样式
 */
import { clsx } from "clsx";

type PillVariant = "default" | "good" | "warning" | "danger" | "info";

const variantStyles: Record<PillVariant, string> = {
  default: "bg-[#eef4ff] text-[#1849a9]",
  good: "bg-[#ecfdf3] text-[#027a48]",
  warning: "bg-[#fffaeb] text-[#936a00]",
  danger: "bg-[#fef3f2] text-[#b42318]",
  info: "bg-[#eef4ff] text-[#155eef]",
};

const statusVariantMap: Record<string, PillVariant> = {
  pending: "default",
  needs_review: "warning",
  confirmed: "good",
  archived: "good",
  exception: "danger",
  ocr_running: "info",
  paid: "good",
  overdue: "danger",
  partial: "warning",
  active: "good",
  expiring: "warning",
  expired: "danger",
  vacant: "default",
};

interface StatusPillProps {
  status: string;
  label?: string;
}

export function StatusPill({ status, label }: StatusPillProps) {
  const variant = statusVariantMap[status] || "default";
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold whitespace-nowrap",
        variantStyles[variant]
      )}
    >
      {label || status}
    </span>
  );
}

interface CategoryPillProps {
  category: string;
}

export function CategoryPill({ category }: CategoryPillProps) {
  return (
    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold whitespace-nowrap bg-[#eef4ff] text-[#1849a9]">
      {category}
    </span>
  );
}

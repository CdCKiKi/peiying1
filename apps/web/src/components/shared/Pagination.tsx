/**
 * 分页导航组件
 */
"use client";

import { clsx } from "clsx";
import { Button } from "./Button";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const startItem = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);

  // 生成页码按钮
  const getPageNumbers = (): (number | "...")[] => {
    const pages: (number | "...")[] = [];
    const showPages = 5; // 最多显示 5 个页码

    if (totalPages <= showPages + 2) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      let start = Math.max(2, page - 2);
      let end = Math.min(totalPages - 1, page + 2);

      if (page <= 3) {
        end = Math.min(showPages, totalPages - 1);
      }
      if (page >= totalPages - 2) {
        start = Math.max(2, totalPages - showPages + 1);
      }

      if (start > 2) pages.push("...");
      for (let i = start; i <= end; i++) pages.push(i);
      if (end < totalPages - 1) pages.push("...");
      pages.push(totalPages);
    }
    return pages;
  };

  if (total === 0) return null;

  return (
    <div className="flex items-center justify-between gap-3 py-2 flex-wrap">
      {/* 左侧：统计信息 */}
      <span className="text-[#667085] text-sm">
        顯示 {startItem}–{endItem}，共 {total} 份
      </span>

      {/* 右侧：翻页控件 */}
      <div className="flex items-center gap-1">
        <Button
          variant="small"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          上一頁
        </Button>

        {getPageNumbers().map((p, i) =>
          p === "..." ? (
            <span key={`dots-${i}`} className="px-1 text-[#667085] text-sm">
              …
            </span>
          ) : (
            <button
              key={p}
              className={clsx(
                "w-8 h-8 rounded-lg text-sm font-medium border-0 cursor-pointer transition-colors",
                p === page
                  ? "bg-[#102a2f] text-white"
                  : "bg-[#f1f5f8] text-[#667085] hover:bg-[#e2e8f0]"
              )}
              onClick={() => onPageChange(p)}
            >
              {p}
            </button>
          )
        )}

        <Button
          variant="small"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          下一頁
        </Button>

        {/* 跳转 */}
        <span className="text-[#667085] text-sm ml-2">跳至</span>
        <input
          type="number"
          className="w-14 border border-[#d8dee6] rounded-lg px-2 py-1 text-sm text-center"
          min={1}
          max={totalPages}
          defaultValue={page}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              const val = parseInt((e.target as HTMLInputElement).value);
              if (val >= 1 && val <= totalPages) onPageChange(val);
            }
          }}
        />

        {/* 每页条数 */}
        {onPageSizeChange && (
          <select
            className="border border-[#d8dee6] rounded-lg px-2 py-1 text-sm ml-2"
            value={pageSize}
            onChange={(e) => onPageSizeChange(parseInt(e.target.value))}
          >
            {[10, 20, 50, 100].map((n) => (
              <option key={n} value={n}>
                {n} 條/頁
              </option>
            ))}
          </select>
        )}
      </div>
    </div>
  );
}

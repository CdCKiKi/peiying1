/**
 * Tommy Dashboard 总览页 - 图表 + 预警 + 逾期追踪
 */
"use client";

import { useState, useEffect } from "react";
import { TommySidebarLayout } from "@/components/modules/tommy/TommySidebarLayout";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/shared/Button";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

// ===== 类型 =====
interface ArchiveStats {
  total: number; pending_review: number; confirmed: number; archived: number;
  exception: number; today_upload: number;
  category_breakdown: { category: string; count: number }[];
  monthly_trend: { month: string; count: number }[];
}
interface RentalStats {
  residential_count: number; parking_count: number; expiring_soon: number;
  vacant: number; total_monthly_rent: number; pending_payments: number;
}
interface ExpiringUnit {
  id: string; unit_number: string; unit_type: string; tenant_name: string | null;
  lease_end: string | null; monthly_rent: number | null;
  remaining_days: number; severity: "danger" | "warning" | "info" | "expired";
}
interface OverduePayment {
  payment_id: string; unit_id: string; unit_number: string; unit_type: string;
  tenant_name: string | null; amount: number; due_date: string;
  overdue_days: number; remaining_days: number; status: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  "租務": "#f59e0b", "財務": "#3b82f6", "人事": "#8b5cf6",
  "教育局通告": "#10b981", "會議": "#ec4899", "其他": "#6b7280",
};
const BAR_COLOR = "#23675f";

// ===== 简易 SVG 饼图组件 =====
function PieChart({ data }: { data: { category: string; count: number }[] }) {
  const total = data.reduce((s, d) => s + d.count, 0) || 1;
  const size = 160; const cx = size / 2; const cy = size / 2; const r = 68;
  let cumulative = 0;

  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} className="shrink-0">
        {data.map((d) => {
          const slice = (d.count / total) * Math.PI * 2;
          const x1 = cx + r * Math.cos(cumulative - Math.PI / 2);
          const y1 = cy + r * Math.sin(cumulative - Math.PI / 2);
          cumulative += slice;
          const x2 = cx + r * Math.cos(cumulative - Math.PI / 2);
          const y2 = cy + r * Math.sin(cumulative - Math.PI / 2);
          const large = slice > Math.PI ? 1 : 0;
          const color = CATEGORY_COLORS[d.category] || "#6b7280";
          return (
            <path
              key={d.category}
              d={`M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`}
              fill={color}
              stroke="white"
              strokeWidth="2"
            />
          );
        })}
        <circle cx={cx} cy={cy} r={r * 0.55} fill="white" />
        <text x={cx} y={cy - 6} textAnchor="middle" fontSize="16" fontWeight="bold" fill="#102a2f">
          {total}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" fontSize="10" fill="#667085">
          總數
        </text>
      </svg>
      <div className="grid gap-1.5 text-sm">
        {data.map((d) => (
          <div key={d.category} className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: CATEGORY_COLORS[d.category] || "#6b7280" }} />
            <span className="text-[#344054]">{d.category}</span>
            <span className="text-[#667085] ml-auto">{d.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ===== 简易 SVG 柱状图组件 =====
function BarChart({ data }: { data: { month: string; count: number }[] }) {
  const maxVal = Math.max(...data.map((d) => d.count), 1);
  const w = data.length * 56 + 20;
  const h = 130;
  const pad = { top: 8, bottom: 22, left: 28, right: 10 };
  const chartW = w - pad.left - pad.right;
  const chartH = h - pad.top - pad.bottom;
  const barW = Math.min(32, chartW / data.length - 12);

  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} style={{ maxWidth: w }}>
      {/* 网格线 */}
      {[0, 0.5, 1].map((pct) => {
        const y = pad.top + chartH * (1 - pct);
        return (
          <g key={pct}>
            <line x1={pad.left} y1={y} x2={pad.left + chartW} y2={y} stroke="#e5e7eb" strokeWidth="1" />
            <text x={pad.left - 4} y={y + 4} textAnchor="end" fontSize="9" fill="#667085">
              {Math.round(maxVal * pct)}
            </text>
          </g>
        );
      })}
      {/* 柱子 */}
      {data.map((d, i) => {
        const barH = (d.count / maxVal) * chartH;
        const x = pad.left + (chartW / data.length) * i + (chartW / data.length - barW) / 2;
        const y = pad.top + chartH - barH;
        return (
          <g key={d.month}>
            <rect x={x} y={y} width={barW} height={Math.max(barH, 1)} rx="3" fill={BAR_COLOR} opacity="0.85" />
            <text x={x + barW / 2} y={pad.top + chartH + 12} textAnchor="middle" fontSize="9" fill="#667085">
              {d.month.slice(5)}
            </text>
            {d.count > 0 && (
              <text x={x + barW / 2} y={y - 4} textAnchor="middle" fontSize="9" fill="#344054" fontWeight="bold">
                {d.count}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

// ===== 主组件 =====
export default function TommyDashboardPage() {
  const router = useRouter();
  const [archiveStats, setArchiveStats] = useState<ArchiveStats | null>(null);
  const [rentalStats, setRentalStats] = useState<RentalStats | null>(null);
  const [expiringUnits, setExpiringUnits] = useState<ExpiringUnit[]>([]);
  const [overduePayments, setOverduePayments] = useState<OverduePayment[]>([]);

  useEffect(() => {
    Promise.all([
      apiFetch<ArchiveStats>("/tommy/archive-documents/stats").catch(() => null),
      apiFetch<RentalStats>("/tommy/rental-units/stats").catch(() => null),
      apiFetch<{ data: ExpiringUnit[] }>("/tommy/rental-units/expiring?days=30").catch(() => null),
      apiFetch<{ data: OverduePayment[] }>("/tommy/rental-units/payments/overdue").catch(() => null),
    ]).then(([a, r, e, o]) => {
      if (a) setArchiveStats(a);
      if (r) setRentalStats(r);
      if (e) setExpiringUnits(e.data);
      if (o) setOverduePayments(o.data);
    });
  }, []);

  // 已到期 + 15天内紧急
  const expiredUnits = expiringUnits.filter((u) => u.severity === "expired");
  const dangerExpiring = expiringUnits.filter((u) => u.severity === "danger");
  // 缴费：逾期 + 7天内待缴
  const trulyOverdue = overduePayments.filter((p) => p.overdue_days > 0);
  const urgentPayments = overduePayments.filter((p) => p.overdue_days === 0 && p.remaining_days <= 7);

  return (
    <TommySidebarLayout>
      <PageHeader eyebrow="TOMMY / 總覽" title="Tommy 工作台" description="快速查看今日待處理的工作事項與關鍵指標。" />

      {/* 统计卡 */}
      <div className="grid grid-cols-4 gap-2.5">
        {[
          { label: "今日上傳", value: archiveStats?.today_upload ?? "-", onClick: () => router.push("/dashboard/tommy/archive") },
          { label: "待復核", value: archiveStats?.pending_review ?? "-", onClick: () => router.push("/dashboard/tommy/archive") },
          { label: "逾期繳費", value: trulyOverdue.length, onClick: () => router.push("/dashboard/tommy/rental"), urgent: trulyOverdue.length > 0 },
          { label: "租務到期", value: expiredUnits.length + dangerExpiring.length, onClick: () => router.push("/dashboard/tommy/rental"), urgent: (expiredUnits.length + dangerExpiring.length) > 0 },
        ].map((item) => (
          <div
            key={item.label}
            className={`border rounded-lg p-3 shadow-[0_10px_30px_rgba(16,24,40,0.08)] cursor-pointer hover:border-[#23675f] transition-colors ${
              item.urgent ? "bg-[#fef2f2] border-[#fca5a5]" : "bg-white border-[#d8dee6]"
            }`}
            onClick={item.onClick}
          >
            <span className={`block text-sm ${item.urgent ? "text-[#dc2626]" : "text-[#667085]"}`}>{item.label}</span>
            <strong className={`block mt-1 text-2xl ${item.urgent ? "text-[#dc2626]" : ""}`}>{item.value}</strong>
          </div>
        ))}
      </div>

      {/* 快捷入口 */}
      <div className="grid grid-cols-2 gap-3 mt-2">
        <div className="bg-white border border-[#d8dee6] rounded-lg p-4 shadow-[0_10px_30px_rgba(16,24,40,0.08)] cursor-pointer hover:border-[#23675f]" onClick={() => router.push("/dashboard/tommy/archive")}>
          <h3 className="text-lg font-bold mb-1">文件智能歸檔</h3>
          <p className="text-[#667085] text-sm">上傳掃描件後，系統自動 OCR、分類、建議檔名並提取關鍵資訊。</p>
          <div className="mt-3"><Button variant="small-primary">進入歸檔</Button></div>
        </div>
        <div className="bg-white border border-[#d8dee6] rounded-lg p-4 shadow-[0_10px_30px_rgba(16,24,40,0.08)] cursor-pointer hover:border-[#23675f]" onClick={() => router.push("/dashboard/tommy/rental")}>
          <h3 className="text-lg font-bold mb-1">租務管理</h3>
          <p className="text-[#667085] text-sm">管理俊傑花園 {rentalStats?.residential_count ?? 8} 個住宅單位及 {rentalStats?.parking_count ?? 9} 個車位的租務事宜。</p>
          <div className="mt-3"><Button variant="small-primary">進入租務</Button></div>
        </div>
      </div>

      {/* 图表区域 */}
      <div className="grid grid-cols-2 gap-3 mt-2">
        {/* 分类分布饼图 */}
        <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-4">
          <h3 className="text-base font-bold mb-3">文件分類分佈</h3>
          {archiveStats?.category_breakdown && archiveStats.category_breakdown.length > 0 ? (
            <PieChart data={archiveStats.category_breakdown} />
          ) : (
            <p className="text-[#667085] text-sm py-8 text-center">尚無數據</p>
          )}
        </section>

        {/* 月度趋势柱状图 */}
        <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-4">
          <h3 className="text-base font-bold mb-3">近 6 個月上傳趨勢</h3>
          {archiveStats?.monthly_trend ? (
            <BarChart data={archiveStats.monthly_trend} />
          ) : (
            <p className="text-[#667085] text-sm py-8 text-center">尚無數據</p>
          )}
        </section>
      </div>

      {/* 预警区域：到期 + 逾期 */}
      <div className="grid grid-cols-2 gap-3 mt-2">
        {/* 租约到期预警 */}
        <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-4">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-base font-bold">租約到期預警</h3>
            <Button variant="small" onClick={() => router.push("/dashboard/tommy/rental")}>查看全部</Button>
          </div>

          {expiringUnits.length === 0 ? (
            <p className="text-[#667085] text-sm py-4 text-center">暫無即將到期租約</p>
          ) : (
            <div className="grid gap-2 max-h-[260px] overflow-auto">
              {/* 已到期 */}
              {expiredUnits.map((u) => (
                <div key={u.id} className="flex justify-between items-center p-2.5 bg-[#fef2f2] border border-[#fecaca] rounded-lg cursor-pointer" onClick={() => router.push("/dashboard/tommy/rental")}>
                  <div>
                    <strong className="text-sm">{u.unit_number}</strong>
                    <span className="text-[#667085] text-xs ml-2">{u.tenant_name || "空置"}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[#dc2626] font-bold text-sm">已到期 {-u.remaining_days} 天</span>
                    <span className="text-[#667085] text-xs block">{u.lease_end}</span>
                  </div>
                </div>
              ))}
              {/* 15天内紧急 */}
              {dangerExpiring.map((u) => (
                <div key={u.id} className="flex justify-between items-center p-2.5 bg-[#fffbeb] border border-[#fde68a] rounded-lg cursor-pointer" onClick={() => router.push("/dashboard/tommy/rental")}>
                  <div>
                    <strong className="text-sm">{u.unit_number}</strong>
                    <span className="text-[#667085] text-xs ml-2">{u.tenant_name || "空置"}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[#d97706] font-bold text-sm">剩 {u.remaining_days} 天</span>
                    <span className="text-[#667085] text-xs block">{u.lease_end}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 逾期缴费追踪 */}
        <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-4">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-base font-bold">繳費逾期追蹤</h3>
            <Button variant="small" onClick={() => router.push("/dashboard/tommy/rental")}>查看全部</Button>
          </div>

          {overduePayments.length === 0 ? (
            <p className="text-[#667085] text-sm py-4 text-center">所有單位已按時繳費 👍</p>
          ) : (
            <div className="grid gap-2 max-h-[260px] overflow-auto">
              {/* 逾期 */}
              {trulyOverdue.map((p) => (
                <div key={p.payment_id} className="flex justify-between items-center p-2.5 bg-[#fef2f2] border border-[#fecaca] rounded-lg cursor-pointer" onClick={() => router.push("/dashboard/tommy/rental")}>
                  <div>
                    <strong className="text-sm">{p.unit_number}</strong>
                    <span className="text-[#667085] text-xs ml-2">{p.tenant_name || "-"}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[#dc2626] font-bold text-sm">逾期 {p.overdue_days} 天</span>
                    <span className="text-[#667085] text-xs block">HK$ {p.amount.toLocaleString()} · {p.due_date}</span>
                  </div>
                </div>
              ))}
              {/* 7天内待缴 */}
              {urgentPayments.map((p) => (
                <div key={p.payment_id} className="flex justify-between items-center p-2.5 bg-[#fffbeb] border border-[#fde68a] rounded-lg cursor-pointer" onClick={() => router.push("/dashboard/tommy/rental")}>
                  <div>
                    <strong className="text-sm">{p.unit_number}</strong>
                    <span className="text-[#667085] text-xs ml-2">{p.tenant_name || "-"}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[#d97706] font-bold text-sm">截止剩 {p.remaining_days} 天</span>
                    <span className="text-[#667085] text-xs block">HK$ {p.amount.toLocaleString()} · {p.due_date}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </TommySidebarLayout>
  );
}

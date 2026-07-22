/**
 * Tommy Dashboard 总览页 - 真实数据
 */
"use client";

import { useState, useEffect } from "react";
import { TommySidebarLayout } from "@/components/modules/tommy/TommySidebarLayout";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/shared/Button";
import { StatusPill } from "@/components/shared/StatusPill";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

interface ArchiveStats {
  total: number; pending_review: number; confirmed: number; archived: number; exception: number; today_upload: number;
}
interface RentalStats {
  residential_count: number; parking_count: number; expiring_soon: number; vacant: number; total_monthly_rent: number; pending_payments: number;
}
interface RecentDoc {
  id: string; original_filename: string; category: string | null; status: string; created_at: string;
}

export default function TommyDashboardPage() {
  const router = useRouter();
  const [archiveStats, setArchiveStats] = useState<ArchiveStats | null>(null);
  const [rentalStats, setRentalStats] = useState<RentalStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<RecentDoc[]>([]);

  useEffect(() => {
    Promise.all([
      apiFetch<ArchiveStats>("/tommy/archive-documents/stats").catch(() => null),
      apiFetch<RentalStats>("/tommy/rental-units/stats").catch(() => null),
      apiFetch<{ data: RecentDoc[] }>("/tommy/archive-documents?page=1&page_size=5").catch(() => null),
    ]).then(([a, r, d]) => {
      if (a) setArchiveStats(a);
      if (r) setRentalStats(r);
      if (d) setRecentDocs(d.data);
    });
  }, []);

  const statusLabels: Record<string, string> = {
    pending: "待處理", needs_review: "待復核", confirmed: "已確認", archived: "已歸檔", exception: "異常",
  };

  return (
    <TommySidebarLayout>
      <PageHeader eyebrow="TOMMY / 總覽" title="Tommy" description="快速查看今日待處理的工作事項。" />

      <div className="grid grid-cols-4 gap-2.5">
        {[
          { label: "今日上傳", value: archiveStats?.today_upload ?? "-", onClick: () => router.push("/dashboard/tommy/archive") },
          { label: "待復核", value: archiveStats?.pending_review ?? "-", onClick: () => router.push("/dashboard/tommy/archive") },
          { label: "已歸檔", value: archiveStats?.archived ?? "-", onClick: () => router.push("/dashboard/tommy/archive") },
          { label: "租務到期", value: rentalStats?.expiring_soon ?? "-", onClick: () => router.push("/dashboard/tommy/rental") },
        ].map((item) => (
          <div
            key={item.label}
            className="bg-white border border-[#d8dee6] rounded-lg p-3 shadow-[0_10px_30px_rgba(16,24,40,0.08)] cursor-pointer hover:border-[#23675f]"
            onClick={item.onClick}
          >
            <span className="block text-[#667085] text-sm">{item.label}</span>
            <strong className="block mt-1 text-2xl">{item.value}</strong>
          </div>
        ))}
      </div>

      {/* 快捷入口 */}
      <div className="grid grid-cols-2 gap-3 mt-2">
        <div
          className="bg-white border border-[#d8dee6] rounded-lg p-4 shadow-[0_10px_30px_rgba(16,24,40,0.08)] cursor-pointer hover:border-[#23675f]"
          onClick={() => router.push("/dashboard/tommy/archive")}
        >
          <h3 className="text-lg font-bold mb-1">文件智能歸檔</h3>
          <p className="text-[#667085] text-sm">上傳掃描件後，系統自動 OCR、分類、建議檔名並提取關鍵資訊。</p>
          <div className="mt-3"><Button variant="small-primary">進入歸檔</Button></div>
        </div>
        <div
          className="bg-white border border-[#d8dee6] rounded-lg p-4 shadow-[0_10px_30px_rgba(16,24,40,0.08)] cursor-pointer hover:border-[#23675f]"
          onClick={() => router.push("/dashboard/tommy/rental")}
        >
          <h3 className="text-lg font-bold mb-1">租務管理</h3>
          <p className="text-[#667085] text-sm">管理俊傑花園 {rentalStats?.residential_count ?? 8} 個住宅單位及 {rentalStats?.parking_count ?? 9} 個車位的租務事宜。</p>
          <div className="mt-3"><Button variant="small-primary">進入租務</Button></div>
        </div>
      </div>

      {/* 最近上传 */}
      {recentDocs.length > 0 && (
        <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-3 mt-2">
          <h3 className="text-base font-bold mb-2">最近上傳文件</h3>
          <table className="w-full border-collapse table-fixed">
            <thead>
              <tr>
                <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "40%" }}>文件名</th>
                <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "20%" }}>分類</th>
                <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "20%" }}>狀態</th>
                <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "20%" }}>時間</th>
              </tr>
            </thead>
            <tbody>
              {recentDocs.map((doc) => (
                <tr key={doc.id} className="bg-white cursor-pointer" onClick={() => router.push("/dashboard/tommy/archive")}>
                  <td className="p-2 text-sm border-b border-[#d8dee6] break-words">{doc.original_filename}</td>
                  <td className="p-2 text-sm border-b border-[#d8dee6]">{doc.category || "-"}</td>
                  <td className="p-2 text-sm border-b border-[#d8dee6]"><StatusPill status={doc.status} label={statusLabels[doc.status]} /></td>
                  <td className="p-2 text-sm border-b border-[#d8dee6] text-[#667085]">{doc.created_at.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </TommySidebarLayout>
  );
}

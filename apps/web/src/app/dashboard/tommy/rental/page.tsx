/**
 * Tommy 租務管理頁面 - 完整功能版
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { TommySidebarLayout } from "@/components/modules/tommy/TommySidebarLayout";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/shared/Button";
import { StatusPill } from "@/components/shared/StatusPill";
import { Modal } from "@/components/shared/Modal";
import { Pagination } from "@/components/shared/Pagination";
import { useToast } from "@/components/shared/Toast";
import { apiFetch, API_BASE } from "@/lib/api";

interface RentalUnit {
  id: string;
  property_name: string;
  unit_number: string;
  unit_type: string;
  tenant_name: string | null;
  tenant_email: string | null;
  lease_start: string | null;
  lease_end: string | null;
  monthly_rent: number | null;
  is_occupied: boolean;
  status: string;
  notes: string | null;
  payments: PaymentRecord[];
  leases: LeaseRecord[];
}

interface LeaseRecord {
  id: string;
  unit_id: string;
  tenant_name: string;
  lease_start: string;
  lease_end: string;
  monthly_rent: number;
  status: string;
  notes: string | null;
  created_at: string;
}

interface PaymentRecord {
  id: string;
  unit_id: string;
  amount: number;
  due_date: string;
  paid_date: string | null;
  paid_amount: number | null;
  status: string;
  reminder_sent: boolean;
  created_at: string;
}

interface AuditLogItem {
  id: string;
  module: string;
  action: string;
  resource_type: string;
  resource_id: string;
  user_id: string;
  user_name: string | null;
  detail: string | null;
  created_at: string;
}

interface RentalStats {
  residential_count: number;
  parking_count: number;
  expiring_soon: number;
  vacant: number;
  total_monthly_rent: number;
  pending_payments: number;
}

const statusLabels: Record<string, string> = {
  active: "已出租",
  expiring: "即將到期",
  expired: "已到期",
  vacant: "空置",
};

const paymentStatusLabels: Record<string, string> = {
  pending: "待繳",
  paid: "已繳",
  overdue: "逾期",
  partial: "部分繳",
};

const leaseStatusLabels: Record<string, string> = {
  active: "當前租約",
  expired: "已到期",
  terminated: "已終止",
};

export default function TommyRentalPage() {
  const { showToast } = useToast();

  const [units, setUnits] = useState<RentalUnit[]>([]);
  const [stats, setStats] = useState<RentalStats | null>(null);
  const [loading, setLoading] = useState(true);

  // 弹窗
  const [newLeaseOpen, setNewLeaseOpen] = useState(false);
  const [detailUnit, setDetailUnit] = useState<RentalUnit | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);

  // 新增租约表单 - 支持新建单位或为已有单位续租
  const [newUnitNumber, setNewUnitNumber] = useState("");
  const [newUnitType, setNewUnitType] = useState("住宅");
  const [newTenant, setNewTenant] = useState("");
  const [newLeaseStart, setNewLeaseStart] = useState("");
  const [newLeaseEnd, setNewLeaseEnd] = useState("");
  const [newRent, setNewRent] = useState("");

  // 分页
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);

  // 续租模式 - 选择已有单位
  const [leaseMode, setLeaseMode] = useState<"new" | "renew">("new");
  const [selectedUnitId, setSelectedUnitId] = useState("");

  // 编辑租约
  const [editLeaseOpen, setEditLeaseOpen] = useState(false);
  const [editingLease, setEditingLease] = useState<LeaseRecord | null>(null);
  const [editTenant, setEditTenant] = useState("");
  const [editLeaseStart, setEditLeaseStart] = useState("");
  const [editLeaseEnd, setEditLeaseEnd] = useState("");
  const [editRent, setEditRent] = useState("");

  // 记录收款
  const [paymentUnit, setPaymentUnit] = useState<RentalUnit | null>(null);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentDueDate, setPaymentDueDate] = useState("");

  // 编辑租户电邮
  const [editingEmailUnitId, setEditingEmailUnitId] = useState<string | null>(null);
  const [editEmailValue, setEditEmailValue] = useState("");

  // 审计日志展开状态
  const [auditExpanded, setAuditExpanded] = useState(false);
  const AUDIT_COLLAPSE_COUNT = 3;

  // ===== 数据加载 =====
  const fetchUnits = useCallback(async (p?: number, ps?: number) => {
    setLoading(true);
    try {
      const currentPage = p ?? page;
      const currentPageSize = ps ?? pageSize;
      const result = await apiFetch<{ data: RentalUnit[]; pagination: { total: number } }>(
        `/tommy/rental-units?page=${currentPage}&page_size=${currentPageSize}`
      );
      setUnits(result.data);
      setTotal(result.pagination.total);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "載入失敗", "error");
    } finally {
      setLoading(false);
    }
  }, [showToast, page, pageSize]);

  const fetchStats = useCallback(async () => {
    try {
      const result = await apiFetch<RentalStats>("/tommy/rental-units/stats");
      setStats(result);
    } catch {
      // 静默
    }
  }, []);

  useEffect(() => {
    fetchUnits();
    fetchStats();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ===== 操作 =====
  const handleSendReminder = async (unitId: string) => {
    try {
      await apiFetch(`/tommy/rental-units/${unitId}/send-reminder`, { method: "POST" });
      showToast("繳費提醒已發送", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "發送失敗", "error");
    }
  };

  const handleGenerateLease = async (unitId: string, unitNumber: string) => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`${API_BASE}/tommy/rental-units/${unitId}/generate-lease`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "下載失敗" }));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `租約_${unitNumber}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("租約文件已生成並下載", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "生成失敗", "error");
    }
  };

  const fetchAuditLogs = async (unitId: string, leaseIds: string[] = [], paymentIds: string[] = []) => {
    try {
      // 查詢與此單位相關的所有審計日誌：單位本身 / 所屬租約 / 所屬繳費
      const allResourceIds = [unitId, ...leaseIds, ...paymentIds];
      const result = await apiFetch<{ data: AuditLogItem[] }>(
        `/audit/logs?module=tommy&page=1&page_size=100`
      );
      const filtered = result.data.filter((l) => allResourceIds.includes(l.resource_id));
      filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setAuditLogs(filtered);
    } catch {
      // 静默
    }
  };

  const handleViewDetail = async (unitId: string) => {
    try {
      const unit = await apiFetch<RentalUnit>(`/tommy/rental-units/${unitId}`);
      setDetailUnit(unit);
      setAuditExpanded(false);
      const leaseIds = unit.leases?.map((l) => l.id) ?? [];
      const paymentIds = unit.payments?.map((p) => p.id) ?? [];
      await fetchAuditLogs(unit.id, leaseIds, paymentIds);
    } catch (err) {
      showToast(err instanceof Error ? err.message : "載入失敗", "error");
    }
  };

  const handleCreateLease = async () => {
    try {
      if (leaseMode === "new") {
        await apiFetch("/tommy/rental-units", {
          method: "POST",
          body: JSON.stringify({
            unit_number: newUnitNumber,
            unit_type: newUnitType,
            tenant_name: newTenant || null,
            lease_start: newLeaseStart || null,
            lease_end: newLeaseEnd || null,
            monthly_rent: newRent ? parseFloat(newRent) : null,
            is_occupied: !!newTenant,
          }),
        });
        showToast("租約已新增", "success");
      } else {
        await apiFetch(`/tommy/rental-units/${selectedUnitId}/leases`, {
          method: "POST",
          body: JSON.stringify({
            tenant_name: newTenant,
            lease_start: newLeaseStart,
            lease_end: newLeaseEnd,
            monthly_rent: parseFloat(newRent),
          }),
        });
        showToast("租約已續租", "success");
      }
      setNewLeaseOpen(false);
      // 清空表单
      setNewUnitNumber(""); setNewTenant(""); setNewLeaseStart(""); setNewLeaseEnd(""); setNewRent("");
      setSelectedUnitId(""); setLeaseMode("new");
      await fetchUnits();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "新增失敗", "error");
    }
  };

  const handleEditLease = (lease: LeaseRecord) => {
    setEditingLease(lease);
    setEditTenant(lease.tenant_name);
    setEditLeaseStart(lease.lease_start);
    setEditLeaseEnd(lease.lease_end);
    setEditRent(String(lease.monthly_rent));
    setEditLeaseOpen(true);
  };

  const handleSaveEditLease = async () => {
    if (!editingLease || !detailUnit) return;
    try {
      await apiFetch(`/tommy/rental-units/${detailUnit.id}/leases/${editingLease.id}`, {
        method: "PUT",
        body: JSON.stringify({
          tenant_name: editTenant,
          lease_start: editLeaseStart,
          lease_end: editLeaseEnd,
          monthly_rent: parseFloat(editRent),
        }),
      });
      showToast("租約已更新", "success");
      setEditLeaseOpen(false);
      setEditingLease(null);
      await fetchUnits();
      if (detailUnit) {
        await handleViewDetail(detailUnit.id);
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "更新失敗", "error");
    }
  };

  const handleCreatePayment = async () => {
    if (!paymentUnit || !paymentAmount || !paymentDueDate) return;
    try {
      await apiFetch(`/tommy/rental-units/${paymentUnit.id}/payments`, {
        method: "POST",
        body: JSON.stringify({
          amount: parseFloat(paymentAmount),
          due_date: paymentDueDate,
        }),
      });
      showToast("繳費記錄已新增", "success");
      setPaymentUnit(null);
      setPaymentAmount(""); setPaymentDueDate("");
      await fetchUnits();
      await fetchStats();
      if (detailUnit && detailUnit.id === paymentUnit.id) {
        await handleViewDetail(paymentUnit.id);
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "新增失敗", "error");
    }
  };

  const handleRecordPayment = async (unitId: string, paymentId: string) => {
    try {
      await apiFetch(`/tommy/rental-units/${unitId}/payments/${paymentId}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: "paid",
          paid_date: new Date().toISOString().slice(0, 10),
          paid_amount: detailUnit?.payments?.find((p) => p.id === paymentId)?.amount ?? null,
        }),
      });
      showToast("已記錄收款", "success");
      await fetchUnits();
      await fetchStats();
      if (detailUnit && detailUnit.id === unitId) {
        await handleViewDetail(unitId);
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失敗", "error");
    }
  };

  const handleVacate = async (unitId: string, unitNumber: string) => {
    if (!confirm(`確定將單位「${unitNumber}」轉為空置嗎？此操作將清空租戶及租約資訊。`)) return;
    try {
      await apiFetch(`/tommy/rental-units/${unitId}/vacate`, { method: "POST" });
      showToast(`單位 ${unitNumber} 已轉為空置`, "success");
      if (detailUnit && detailUnit.id === unitId) {
        setDetailUnit(null);
      }
      await fetchUnits();
      await fetchStats();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失敗", "error");
    }
  };

  const handleDeleteUnit = async (unitId: string, unitNumber: string) => {
    if (!confirm(`確定要刪除單位「${unitNumber}」嗎？此操作將同時刪除其所有租約和繳費記錄，且不可撤銷。`)) return;
    try {
      await apiFetch(`/tommy/rental-units/${unitId}`, { method: "DELETE" });
      showToast(`單位 ${unitNumber} 已刪除`, "success");
      if (detailUnit && detailUnit.id === unitId) {
        setDetailUnit(null);
      }
      await fetchUnits();
      await fetchStats();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "刪除失敗", "error");
    }
  };

  const handleUndoPayment = async (unitId: string, paymentId: string) => {
    if (!confirm("確定要撤銷此次繳費記錄嗎？")) return;
    try {
      await apiFetch(`/tommy/rental-units/${unitId}/payments/${paymentId}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: "pending",
          paid_date: null,
          paid_amount: null,
        }),
      });
      showToast("繳費記錄已撤銷", "success");
      await fetchUnits();
      await fetchStats();
      if (detailUnit) {
        handleViewDetail(detailUnit.id);
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失敗", "error");
    }
  };

  const handleExport = () => {
    const headers = ["單位", "類型", "租戶", "月租", "租約到期", "狀態"];
    const rows = units.map((u) => [
      u.unit_number, u.unit_type, u.tenant_name || "",
      u.monthly_rent ? `HK$ ${u.monthly_rent}` : "",
      u.lease_end || "", statusLabels[u.status] || u.status,
    ]);
    const csv = [headers, ...rows].map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "rental_units.csv"; a.click();
    URL.revokeObjectURL(url);
    showToast("報表已導出", "success");
  };

  // ===== 计算数据 =====
  const residentialUnits = units.filter((u) => u.unit_type === "住宅");
  const parkingUnits = units.filter((u) => u.unit_type === "車位");

  const today = new Date().toISOString().slice(0, 10);

  const renderUnitRow = (unit: RentalUnit) => {
    const pendingPayment = unit.payments?.find((p) => p.status === "pending" || p.status === "overdue");
    // 计算缴费逾期/紧急天数
    let overdueDays = 0;
    let paymentOverdue = false;
    let paymentUrgent = false;
    let paymentUrgentDays = 0;
    if (pendingPayment) {
      const dueTime = new Date(pendingPayment.due_date).getTime();
      const diffDays = Math.floor((Date.now() - dueTime) / 86400000);
      if (diffDays > 0) {
        overdueDays = diffDays;
        paymentOverdue = true;
      } else if (diffDays > -8) {
        // 剩余 1~7 天（diffDays 为 -7 ~ -1）
        paymentUrgent = true;
        paymentUrgentDays = -diffDays;
      }
    }
    // 计算租约剩余天数（用整天差值，与后端 date diff 一致）
    let leaseRemaining = 0;
    let leaseUrgent = false;
    let leaseExpired = false;
    if (unit.lease_end) {
      const endDate = new Date(unit.lease_end);
      const todayDate = new Date(today);
      leaseRemaining = Math.floor((endDate.getTime() - todayDate.getTime()) / 86400000);
      leaseUrgent = leaseRemaining <= 15 && leaseRemaining >= 0;
      leaseExpired = leaseRemaining < 0;
    }
    // 动态计算租务状态
    const effectiveStatus = leaseExpired ? "expired" : leaseUrgent ? "expiring" : unit.status;
    // 提醒按钮：逾期 或 待缴且剩余<=7天
    const showReminder = paymentOverdue || paymentUrgent;

    return (
      <tr key={unit.id} className={`${paymentOverdue || leaseExpired ? "bg-[#fef2f2]" : paymentUrgent || leaseUrgent ? "bg-[#fff7ed]" : "bg-white"}`}>
        <td className="p-2 text-sm border-b border-[#d8dee6]">{unit.unit_number}</td>
        <td className="p-2 text-sm border-b border-[#d8dee6]">{unit.tenant_name || "-"}</td>
        <td className="p-2 text-sm border-b border-[#d8dee6]">{unit.monthly_rent ? `HK$ ${Number(unit.monthly_rent).toLocaleString()}` : "-"}</td>
        <td className={`p-2 text-sm border-b border-[#d8dee6] ${leaseExpired ? "text-[#dc2626] font-bold" : leaseUrgent ? "text-[#d97706] font-bold" : ""}`}>
          {unit.lease_end || "-"}
          {leaseUrgent && unit.lease_end && <span className="block text-[#d97706] text-xs">剩 {leaseRemaining} 天</span>}
          {leaseExpired && unit.lease_end && <span className="block text-[#dc2626] text-xs">已到期 {-leaseRemaining} 天</span>}
        </td>
        <td className="p-2 text-sm border-b border-[#d8dee6]">
          {paymentOverdue ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#fecaca] text-[#991b1b] text-xs font-bold rounded-full">
              逾期 {overdueDays} 天
            </span>
          ) : paymentUrgent ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#fef3c7] text-[#92400e] text-xs font-bold rounded-full">
              截止剩 {paymentUrgentDays} 天
            </span>
          ) : pendingPayment ? (
            <StatusPill status="pending" label={paymentStatusLabels[pendingPayment.status]} />
          ) : unit.is_occupied ? (
            <StatusPill status="paid" label="已繳" />
          ) : "-"}
        </td>
        <td className="p-2 text-sm border-b border-[#d8dee6]">
          <StatusPill status={effectiveStatus} label={statusLabels[effectiveStatus] || effectiveStatus} />
        </td>
        <td className="p-2 text-sm border-b border-[#d8dee6]">
          <div className="flex gap-1 flex-wrap">
            <Button variant="small" onClick={() => handleViewDetail(unit.id)}>查看</Button>
            {showReminder && <Button variant="small-primary" onClick={() => handleSendReminder(unit.id)}>提醒</Button>}
            {pendingPayment && <Button variant="small" onClick={() => handleRecordPayment(unit.id, pendingPayment.id)}>收款</Button>}
            {effectiveStatus === "expired" && <Button variant="small-primary" onClick={() => handleVacate(unit.id, unit.unit_number)}>轉為空置</Button>}
            {effectiveStatus === "vacant" && <Button variant="small-primary" onClick={() => setNewLeaseOpen(true)}>新增租約</Button>}
            <Button variant="small-ghost" onClick={() => setPaymentUnit(unit)}>新增繳費</Button>
            <Button variant="small-ghost" onClick={() => handleDeleteUnit(unit.id, unit.unit_number)} className="text-[#dc2626]">刪除</Button>
          </div>
        </td>
      </tr>
    );
  };

  return (
    <TommySidebarLayout>
      <PageHeader
        eyebrow="TOMMY / 租務管理"
        title="俊傑花園租務儀表板"
        description="集中管理 8 個住宅單位及 9 個車位的租約、繳費與到期提醒。"
        actions={
          <>
            <Button variant="ghost" onClick={handleExport}>導出報表</Button>
            <Button variant="primary" onClick={() => setNewLeaseOpen(true)}>新增租約</Button>
          </>
        }
      />

      {/* 统计卡 */}
      <div className="grid grid-cols-4 gap-2.5">
        {[
          { label: "住宅單位", value: stats?.residential_count ?? "-" },
          { label: "車位", value: stats?.parking_count ?? "-" },
          { label: "即將到期", value: stats?.expiring_soon ?? "-" },
          { label: "月租總額", value: stats ? `HK$ ${stats.total_monthly_rent.toLocaleString()}` : "-" },
        ].map((item) => (
          <div key={item.label} className="bg-white border border-[#d8dee6] rounded-lg p-3 shadow-[0_10px_30px_rgba(16,24,40,0.08)]">
            <span className="block text-[#667085] text-sm">{item.label}</span>
            <strong className="block mt-1 text-2xl">{item.value}</strong>
          </div>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-8 text-[#667085]">載入中...</div>
      ) : (
        <>
          {/* 住宅单位列表 */}
          <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-3 mt-2">
            <h3 className="text-base font-bold mb-2">住宅單位 ({residentialUnits.length})</h3>
            <div className="overflow-auto">
              <table className="w-full border-collapse table-fixed">
                <thead>
                  <tr>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "14%" }}>單位</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "12%" }}>租戶</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "12%" }}>月租</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "12%" }}>租約到期</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "10%" }}>繳費</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "10%" }}>租務狀態</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "30%" }}>操作</th>
                  </tr>
                </thead>
                <tbody>{residentialUnits.map(renderUnitRow)}</tbody>
              </table>
            </div>
          </section>

          {/* 车位列表 */}
          <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-3 mt-2">
            <h3 className="text-base font-bold mb-2">車位 ({parkingUnits.length})</h3>
            <div className="overflow-auto">
              <table className="w-full border-collapse table-fixed">
                <thead>
                  <tr>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "14%" }}>車位編號</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "12%" }}>租戶</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "12%" }}>月租</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "12%" }}>租約到期</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "10%" }}>繳費</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "10%" }}>租務狀態</th>
                    <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "30%" }}>操作</th>
                  </tr>
                </thead>
                <tbody>{parkingUnits.map(renderUnitRow)}</tbody>
              </table>
            </div>
          </section>

          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            onPageChange={(p) => { setPage(p); fetchUnits(p, pageSize); }}
            onPageSizeChange={(ps) => { setPageSize(ps); setPage(1); fetchUnits(1, ps); }}
          />
        </>
      )}

      {/* 新增租约弹窗 */}
      <Modal open={newLeaseOpen} onClose={() => { setNewLeaseOpen(false); setNewUnitNumber(""); setNewTenant(""); setNewLeaseStart(""); setNewLeaseEnd(""); setNewRent(""); setSelectedUnitId(""); setLeaseMode("new"); }} title={leaseMode === "new" ? "新增租約" : "續租"} description={leaseMode === "new" ? "新增租賃單位及租戶資訊。" : "為已有單位新增租約，舊租約將自動標記為已到期。"}>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2 grid grid-cols-2 gap-2">
            <Button variant={leaseMode === "new" ? "primary" : "ghost"} onClick={() => setLeaseMode("new")}>新建單位</Button>
            <Button variant={leaseMode === "renew" ? "primary" : "ghost"} onClick={() => setLeaseMode("renew")}>為已有單位續租</Button>
          </div>

          {leaseMode === "new" && (
            <>
              <div className="grid gap-1">
                <label className="text-[#344054] font-bold text-sm">單位編號 *</label>
                <input className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={newUnitNumber} onChange={(e) => setNewUnitNumber(e.target.value)} placeholder="如 A座8樓B室" />
              </div>
              <div className="grid gap-1">
                <label className="text-[#344054] font-bold text-sm">類型</label>
                <select className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={newUnitType} onChange={(e) => setNewUnitType(e.target.value)}>
                  <option>住宅</option>
                  <option>車位</option>
                </select>
              </div>
            </>
          )}

          {leaseMode === "renew" && (
            <div className="grid gap-1 col-span-2">
              <label className="text-[#344054] font-bold text-sm">選擇單位 *</label>
              <select className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={selectedUnitId} onChange={(e) => setSelectedUnitId(e.target.value)}>
                <option value="">請選擇單位</option>
                {units.map((u) => (
                  <option key={u.id} value={u.id}>{u.unit_number} {u.tenant_name ? `(當前租戶: ${u.tenant_name})` : "(空置)"}</option>
                ))}
              </select>
            </div>
          )}

          <div className="grid gap-1">
            <label className="text-[#344054] font-bold text-sm">租戶名稱 *</label>
            <input className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={newTenant} onChange={(e) => setNewTenant(e.target.value)} placeholder="如 陳先生" />
          </div>
          <div className="grid gap-1">
            <label className="text-[#344054] font-bold text-sm">月租 (HK$) *</label>
            <input type="number" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={newRent} onChange={(e) => setNewRent(e.target.value)} placeholder="如 18500" />
          </div>
          <div className="grid gap-1">
            <label className="text-[#344054] font-bold text-sm">租約開始 *</label>
            <input type="date" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={newLeaseStart} onChange={(e) => setNewLeaseStart(e.target.value)} />
          </div>
          <div className="grid gap-1">
            <label className="text-[#344054] font-bold text-sm">租約到期 *</label>
            <input type="date" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={newLeaseEnd} onChange={(e) => setNewLeaseEnd(e.target.value)} />
          </div>
          <div className="col-span-2 flex gap-2 mt-2">
            <Button variant="primary" onClick={handleCreateLease} disabled={leaseMode === "new" ? !newUnitNumber : !selectedUnitId || !newTenant || !newRent || !newLeaseStart || !newLeaseEnd}>
              {leaseMode === "new" ? "確認新增" : "確認續租"}
            </Button>
            <Button variant="ghost" onClick={() => setNewLeaseOpen(false)}>取消</Button>
          </div>
        </div>
      </Modal>

      {/* 单位详情弹窗 */}
      <Modal open={!!detailUnit} onClose={() => setDetailUnit(null)} title="單位詳情" description={detailUnit?.unit_number}>
        {detailUnit && (
          <div className="grid gap-3">
            <div className="grid grid-cols-2 gap-3">
              <div><span className="text-[#667085] text-sm">物業：</span><strong>{detailUnit.property_name}</strong></div>
              <div><span className="text-[#667085] text-sm">類型：</span><strong>{detailUnit.unit_type}</strong></div>
              <div><span className="text-[#667085] text-sm">租戶：</span><strong>{detailUnit.tenant_name || "空置"}</strong></div>
              <div>
                <span className="text-[#667085] text-sm">電郵：</span>
                {editingEmailUnitId === detailUnit.id ? (
                  <span className="inline-flex gap-1">
                    <input className="border border-[#d8dee6] rounded px-2 py-0.5 text-sm w-48" value={editEmailValue} onChange={(e) => setEditEmailValue(e.target.value)} placeholder="租戶電郵地址" />
                    <Button variant="small-primary" onClick={async () => {
                      try {
                        await apiFetch(`/tommy/rental-units/${detailUnit.id}`, { method: "PATCH", body: JSON.stringify({ tenant_email: editEmailValue }) });
                        showToast("電郵已更新", "success");
                        setEditingEmailUnitId(null);
                        handleViewDetail(detailUnit.id);
                      } catch (err) { showToast(err instanceof Error ? err.message : "更新失敗", "error"); }
                    }}>保存</Button>
                    <Button variant="small-ghost" onClick={() => setEditingEmailUnitId(null)}>取消</Button>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2">
                    <strong>{detailUnit.tenant_email || "未設定"}</strong>
                    <Button variant="small" onClick={() => { setEditingEmailUnitId(detailUnit.id); setEditEmailValue(detailUnit.tenant_email || ""); }}>編輯</Button>
                  </span>
                )}
              </div>
              <div><span className="text-[#667085] text-sm">月租：</span><strong>HK$ {Number(detailUnit.monthly_rent || 0).toLocaleString()}</strong></div>
              <div><span className="text-[#667085] text-sm">租約開始：</span><strong>{detailUnit.lease_start || "-"}</strong></div>
              <div><span className="text-[#667085] text-sm">租約到期：</span><strong>{detailUnit.lease_end || "-"}</strong></div>
            </div>

            <div>
              <h3 className="text-base font-bold mb-2">租約記錄</h3>
              {detailUnit.leases && detailUnit.leases.length > 0 ? (
                <table className="w-full border-collapse table-fixed">
                  <thead>
                    <tr>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]">租戶</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]">月租</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]">租約期間</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]">狀態</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detailUnit.leases.map((l) => (
                      <tr key={l.id} className="bg-white">
                        <td className="p-2 text-sm border-b border-[#d8dee6]">{l.tenant_name}</td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">HK$ {Number(l.monthly_rent).toLocaleString()}</td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">{l.lease_start} ~ {l.lease_end}</td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">
                          <StatusPill status={l.status === "active" ? "paid" : l.status === "expired" ? "pending" : "overdue"} label={leaseStatusLabels[l.status]} />
                        </td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">
                          <Button variant="small" onClick={() => handleEditLease(l)}>編輯</Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-[#667085] text-sm">暫無租約記錄</p>
              )}
            </div>

            <div>
              <h3 className="text-base font-bold mb-2">繳費記錄</h3>
              {detailUnit.payments && detailUnit.payments.length > 0 ? (
                <table className="w-full border-collapse table-fixed">
                  <thead>
                    <tr>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]">應繳金額</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]">截止日</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]">已繳日期</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]">狀態</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detailUnit.payments.map((p) => (
                      <tr key={p.id} className="bg-white">
                        <td className="p-2 text-sm border-b border-[#d8dee6]">HK$ {Number(p.amount).toLocaleString()}</td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">{p.due_date}</td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">{p.paid_date || "-"}</td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]"><StatusPill status={p.status} label={paymentStatusLabels[p.status]} /></td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">
                          {p.status === "paid" && (
                            <Button variant="small-danger" onClick={() => handleUndoPayment(detailUnit.id, p.id)}>撤銷</Button>
                          )}
                          {p.status === "pending" && (
                            <Button variant="small" onClick={() => handleRecordPayment(detailUnit.id, p.id)}>收款</Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-[#667085] text-sm">暫無繳費記錄</p>
              )}
            </div>

            {/* 审计日志 */}
            <div>
              <h3 className="text-base font-bold mb-2">審計日誌</h3>
              {auditLogs.length > 0 ? (
                <div className="border border-[#d8dee6] rounded-lg overflow-hidden">
                  <ul>
                    {(auditExpanded ? auditLogs : auditLogs.slice(0, AUDIT_COLLAPSE_COUNT)).map((log, idx, arr) => (
                      <li key={log.id} className={`flex gap-3 px-3 py-2 text-sm ${idx !== 0 ? "border-t border-[#eef1f5]" : ""}`}>
                        <span className="shrink-0 text-[#667085] text-xs mt-0.5 whitespace-nowrap">
                          {new Date(log.created_at).toLocaleString("zh-HK", { hour12: false })}
                        </span>
                        <span className="text-[#344054] leading-relaxed">
                          <span className="font-bold text-[#1d2939]">{log.user_name || "系統"}</span>
                          <span className="mx-1">·</span>
                          <span className="text-[#23675f] font-bold">{log.action}</span>
                          {log.detail && <span>：{log.detail}</span>}
                        </span>
                      </li>
                    ))}
                  </ul>
                  {auditLogs.length > AUDIT_COLLAPSE_COUNT && (
                    <button
                      className="w-full text-center text-sm text-[#23675f] font-bold py-2 bg-[#f8fafc] hover:bg-[#eef7f5] transition-colors border-t border-[#eef1f5]"
                      onClick={() => setAuditExpanded((v) => !v)}
                    >
                      {auditExpanded ? "收起 ↑" : `展開更多 (${auditLogs.length - AUDIT_COLLAPSE_COUNT} 條) ↓`}
                    </button>
                  )}
                </div>
              ) : (
                <p className="text-[#667085] text-sm">暫無審計日誌</p>
              )}
            </div>

            <div className="flex gap-2 flex-wrap">
              <Button variant="primary" onClick={() => handleGenerateLease(detailUnit.id, detailUnit.unit_number)}>生成租約文件</Button>
              <Button variant="default" onClick={() => handleSendReminder(detailUnit.id)}>發送繳費提醒</Button>
              <Button variant="ghost" onClick={() => { setSelectedUnitId(detailUnit.id); setLeaseMode("renew"); setNewLeaseOpen(true); setDetailUnit(null); }}>新增租約</Button>
              {detailUnit.status === "expired" && <Button variant="primary" onClick={() => handleVacate(detailUnit.id, detailUnit.unit_number)}>轉為空置</Button>}
              <Button variant="ghost" onClick={() => handleDeleteUnit(detailUnit.id, detailUnit.unit_number)} className="text-[#dc2626] ml-auto">刪除此單位</Button>
            </div>
          </div>
        )}
      </Modal>

      {/* 记录缴费弹窗 */}
      <Modal open={!!paymentUnit} onClose={() => { setPaymentUnit(null); setPaymentAmount(""); setPaymentDueDate(""); }} title="新增繳費" description={paymentUnit?.unit_number} width="440px">
        {paymentUnit && (
          <div className="grid gap-3">
            <div className="grid gap-1">
              <label className="text-[#344054] font-bold text-sm">應繳金額 (HK$) *</label>
              <input type="number" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={paymentAmount} onChange={(e) => setPaymentAmount(e.target.value)} placeholder={paymentUnit.monthly_rent ? String(paymentUnit.monthly_rent) : ""} />
            </div>
            <div className="grid gap-1">
              <label className="text-[#344054] font-bold text-sm">繳費截止日 *</label>
              <input type="date" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={paymentDueDate} onChange={(e) => setPaymentDueDate(e.target.value)} />
            </div>
            <div className="flex gap-2 mt-2">
              <Button variant="primary" onClick={handleCreatePayment} disabled={!paymentAmount || !paymentDueDate}>確認新增</Button>
              <Button variant="ghost" onClick={() => setPaymentUnit(null)}>取消</Button>
            </div>
          </div>
        )}
      </Modal>

      {/* 编辑租约弹窗 */}
      <Modal open={editLeaseOpen} onClose={() => { setEditLeaseOpen(false); setEditingLease(null); }} title="編輯租約" description="修改租約信息">
        <div className="grid grid-cols-2 gap-3">
          <div className="grid gap-1 col-span-2">
            <label className="text-[#344054] font-bold text-sm">租戶名稱 *</label>
            <input className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={editTenant} onChange={(e) => setEditTenant(e.target.value)} placeholder="請輸入租戶名稱" />
          </div>
          <div className="grid gap-1">
            <label className="text-[#344054] font-bold text-sm">月租 (HK$) *</label>
            <input type="number" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={editRent} onChange={(e) => setEditRent(e.target.value)} placeholder="請輸入月租金" />
          </div>
          <div className="grid gap-1">
            <label className="text-[#344054] font-bold text-sm">租約開始日期 *</label>
            <input type="date" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={editLeaseStart} onChange={(e) => setEditLeaseStart(e.target.value)} />
          </div>
          <div className="grid gap-1 col-span-2">
            <label className="text-[#344054] font-bold text-sm">租約到期日期 *</label>
            <input type="date" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={editLeaseEnd} onChange={(e) => setEditLeaseEnd(e.target.value)} />
          </div>
          <div className="flex gap-2 mt-2 col-span-2">
            <Button variant="primary" onClick={handleSaveEditLease} disabled={!editTenant || !editRent || !editLeaseStart || !editLeaseEnd}>確認保存</Button>
            <Button variant="ghost" onClick={() => { setEditLeaseOpen(false); setEditingLease(null); }}>取消</Button>
          </div>
        </div>
      </Modal>
    </TommySidebarLayout>
  );
}

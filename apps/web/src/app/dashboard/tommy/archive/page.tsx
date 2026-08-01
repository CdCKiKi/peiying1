/**
 * Tommy 文件歸檔頁面 - 完整功能版
 * 对标 前端页面参考.html，所有按钮接入后端 API
 */
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { clsx } from "clsx";
import { TommySidebarLayout } from "@/components/modules/tommy/TommySidebarLayout";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/shared/Button";
import { StatusPill, CategoryPill } from "@/components/shared/StatusPill";
import { Modal } from "@/components/shared/Modal";
import { UploadDropzone } from "@/components/shared/UploadDropzone";
import { Pagination } from "@/components/shared/Pagination";
import { useToast } from "@/components/shared/Toast";
import { apiFetch, apiUpload, getFileUrl } from "@/lib/api";

// ===== 类型定义 =====
interface ArchiveDoc {
  id: string;
  original_file_id: string;
  original_filename: string;
  category: string | null;
  suggested_name: string | null;
  amount: number | null;
  due_date: string | null;
  ocr_text: string | null;
  ai_summary: string | null;
  confidence: string | null;
  status: string;
  last_reviewed_by: string | null;
  last_reviewed_at: string | null;
  created_at: string;
  note: string | null;
}

interface ArchiveStats {
  total: number;
  pending_review: number;
  confirmed: number;
  archived: number;
  exception: number;
  today_upload: number;
}

interface AuditLog {
  id: string;
  action: string;
  detail: string | null;
  user_name: string | null;
  created_at: string;
}

const statusLabels: Record<string, string> = {
  pending: "待處理",
  needs_review: "待確認",
  confirmed: "已確認",
  archived: "已歸檔",
  exception: "異常",
  ocr_running: "OCR 處理中",
};

export default function TommyArchivePage() {
  const { showToast } = useToast();

  // ===== 状态 =====
  const [docs, setDocs] = useState<ArchiveDoc[]>([]);
  const [stats, setStats] = useState<ArchiveStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDoc, setSelectedDoc] = useState<ArchiveDoc | null>(null);

  // 分类标签状态
  type TabType = "all" | "needs_review" | "confirmed" | "archived";
  const [activeTab, setActiveTab] = useState<TabType>("all");

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    setPage(1);
    setSelectedIds(new Set());
    if (tab === "all") {
      setFilterStatus("");
    } else {
      setFilterStatus(tab);
    }
  };

  // 弹窗状态
  const [uploadOpen, setUploadOpen] = useState(false);
  const [actionsOpen, setActionsOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFileUrl, setPreviewFileUrl] = useState("");
  const [previewFilename, setPreviewFilename] = useState("");
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  // 搜索/筛选状态
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  // 批量操作状态
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchOperating, setBatchOperating] = useState(false);

  // 分页状态
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  // 日期筛选状态
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // 自动轮询（正在处理的文档）
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // 预览用的 blob URL 引用，关闭弹窗时需 revoke 避免内存泄漏
  const previewBlobUrlRef = useRef<string>("");

  // 编辑状态
  const [editCategory, setEditCategory] = useState("");
  const [editFilename, setEditFilename] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [editDueDate, setEditDate] = useState("");

  // ===== 数据加载 =====
  const fetchDocs = useCallback(async (p?: number, ps?: number) => {
    const currentPage = p ?? page;
    const currentPageSize = ps ?? pageSize;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterCategory) params.set("category", filterCategory);
      if (filterStatus) params.set("status", filterStatus);
      if (searchQuery) params.set("search", searchQuery);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      params.set("page", String(currentPage));
      params.set("page_size", String(currentPageSize));

      const result = await apiFetch<{ data: ArchiveDoc[]; pagination: { page: number; page_size: number; total: number } }>(
        `/tommy/archive-documents?${params.toString()}`
      );
      setDocs(result.data);
      setTotal(result.pagination.total);
      if (result.data.length > 0 && !selectedDoc) {
        setSelectedDoc(result.data[0]);
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "載入失敗", "error");
    } finally {
      setLoading(false);
    }
  }, [filterCategory, filterStatus, searchQuery, dateFrom, dateTo, page, pageSize, showToast]);

  const fetchStats = useCallback(async () => {
    try {
      const result = await apiFetch<ArchiveStats>("/tommy/archive-documents/stats");
      setStats(result);
    } catch {
      // 静默失败
    }
  }, []);

  useEffect(() => {
    fetchDocs(1, pageSize);
    fetchStats();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // 筛选/搜索变化时重新加载
  useEffect(() => {
    fetchDocs(1, pageSize);
    fetchStats();
  }, [filterCategory, filterStatus, searchQuery, dateFrom, dateTo]); // eslint-disable-line react-hooks/exhaustive-deps

  // 自动轮询：有 pending/ocr_running 状态的文档时每 3 秒刷新
  // 用 ref 保存最新的 fetch 函数，避免 effect 依赖频繁变化的 useCallback
  // 否则每次 docs 更新都会重建 setInterval，且可能捕获过期的 fetchDocs 闭包。
  const fetchDocsRef = useRef(fetchDocs);
  const fetchStatsRef = useRef(fetchStats);
  useEffect(() => {
    fetchDocsRef.current = fetchDocs;
    fetchStatsRef.current = fetchStats;
  });

  const hasProcessing = docs.some((d) => d.status === "pending" || d.status === "ocr_running");
  useEffect(() => {
    if (!hasProcessing) return;
    pollingRef.current = setInterval(() => {
      fetchDocsRef.current();
      fetchStatsRef.current();
    }, 3000);
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [hasProcessing]);

  // ===== 选中文档时更新编辑状态 =====
  const handleSelectDoc = (doc: ArchiveDoc) => {
    setSelectedDoc(doc);
    setEditCategory(doc.category || "其他");
    setEditFilename(doc.suggested_name || "");
    setEditAmount(doc.amount ? String(doc.amount) : "");
    setEditDate(doc.due_date || "");
  };

  // ===== 获取审计日志 =====
  const fetchAuditLogs = async (docId: string) => {
    try {
      const result = await apiFetch<{ data: AuditLog[] }>(
        `/audit/logs?resource_id=${docId}&page=1&page_size=20`
      );
      setAuditLogs(result.data);
    } catch {
      setAuditLogs([]);
    }
  };

  // ===== 上传成功回调 =====
  const handleUploadSuccess = async (_fileId: string, filename: string) => {
    showToast(`文件 ${filename} 上傳成功，正在處理...`, "success");
    setUploadOpen(false);
    await fetchDocs();
    await fetchStats();
  };

  // ===== 操作按钮 =====
  const handleConfirm = async () => {
    if (!selectedDoc) return;
    try {
      // 先更新字段
      await apiFetch(`/tommy/archive-documents/${selectedDoc.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          category: editCategory,
          suggested_name: editFilename,
          amount: editAmount ? parseFloat(editAmount) : null,
          due_date: editDueDate || null,
        }),
      });
      // 再确认
      await apiFetch(`/tommy/archive-documents/${selectedDoc.id}/confirm`, { method: "POST" });
      showToast("AI 結果已確認，審計日誌已記錄", "success");
      await fetchDocs();
      await fetchStats();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失敗", "error");
    }
  };

  const handleArchive = async () => {
    if (!selectedDoc) return;
    try {
      // 先确认
      await apiFetch(`/tommy/archive-documents/${selectedDoc.id}/confirm`, { method: "POST" });
      // 再归档
      await apiFetch(`/tommy/archive-documents/${selectedDoc.id}/archive`, { method: "POST" });
      showToast("文件已歸檔", "success");
      await fetchDocs();
      await fetchStats();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失敗", "error");
    }
  };

  const handleFlagException = async () => {
    if (!selectedDoc) return;
    try {
      await apiFetch(`/tommy/archive-documents/${selectedDoc.id}/flag-exception`, { method: "POST" });
      showToast("已標記異常，等待人工處理", "warning");
      await fetchDocs();
      await fetchStats();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失敗", "error");
    }
  };

  const handleRetry = async (docId: string) => {
    try {
      await apiFetch(`/tommy/archive-documents/${docId}/retry`, { method: "POST" });
      showToast("已重新執行 OCR 和 AI 分類", "success");
      await fetchDocs();
      await fetchStats();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "重試失敗", "error");
    }
  };

  // ===== 批量操作 =====

  const toggleSelect = (docId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) { next.delete(docId); } else { next.add(docId); }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === docs.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(docs.map((d) => d.id)));
    }
  };

  const handleBatchConfirm = async () => {
    if (selectedIds.size === 0) return;
    setBatchOperating(true);
    try {
      const result = await apiFetch<{ confirmed: number; errors: string[] }>("/tommy/archive-documents/batch/confirm", {
        method: "POST",
        body: JSON.stringify({ doc_ids: Array.from(selectedIds) }),
      });
      showToast(`已批量確認 ${result.confirmed} 份文件`, "success");
      if (result.errors.length > 0) {
        showToast(`部分失敗: ${result.errors.join("; ")}`, "error");
      }
      setSelectedIds(new Set());
      await fetchDocs();
      await fetchStats();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "批量操作失敗", "error");
    } finally {
      setBatchOperating(false);
    }
  };

  const handleBatchArchive = async () => {
    if (selectedIds.size === 0) return;
    setBatchOperating(true);
    try {
      const result = await apiFetch<{ archived: number; errors: string[] }>("/tommy/archive-documents/batch/archive", {
        method: "POST",
        body: JSON.stringify({ doc_ids: Array.from(selectedIds) }),
      });
      showToast(`已批量歸檔 ${result.archived} 份文件`, "success");
      if (result.errors.length > 0) {
        showToast(`部分失敗: ${result.errors.join("; ")}`, "error");
      }
      setSelectedIds(new Set());
      await fetchDocs();
      await fetchStats();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "批量操作失敗", "error");
    } finally {
      setBatchOperating(false);
    }
  };

  const handleBatchRetry = async () => {
    if (selectedIds.size === 0) return;
    setBatchOperating(true);
    try {
      const result = await apiFetch<{ retried: number; errors: string[] }>("/tommy/archive-documents/batch/retry", {
        method: "POST",
        body: JSON.stringify({ doc_ids: Array.from(selectedIds) }),
      });
      showToast(`已批量重試 ${result.retried} 份文件`, "success");
      if (result.errors.length > 0) {
        showToast(`部分失敗: ${result.errors.join("; ")}`, "error");
      }
      setSelectedIds(new Set());
      await fetchDocs();
      await fetchStats();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "批量操作失敗", "error");
    } finally {
      setBatchOperating(false);
    }
  };

  const handleRunOcr = async () => {
    if (!selectedDoc) return;
    try {
      await apiFetch(`/tommy/archive-documents/${selectedDoc.id}/run-ocr`, { method: "POST" });
      showToast("OCR 重新識別完成", "success");
      await fetchDocs();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失敗", "error");
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await apiFetch(`/tommy/archive-documents/${docId}`, { method: "DELETE" });
      showToast("已刪除", "success");
      await fetchDocs();
      await fetchStats();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "刪除失敗", "error");
    }
  };

  const handleUndoArchive = async (docId: string) => {
    if (!confirm("確定要撤銷此次操作嗎？")) return;
    try {
      await apiFetch(`/tommy/archive-documents/${docId}/undo-archive`, { method: "POST" });
      showToast("操作已撤銷", "success");
      await fetchDocs();
      await fetchStats();
      if (selectedDoc?.id === docId) {
        handleSelectDoc(docs.find((d) => d.id === docId) || docs[0]);
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "操作失敗", "error");
    }
  };

  // ===== 详情弹窗 =====
  const handleOpenDetail = async () => {
    if (!selectedDoc) return;
    await fetchAuditLogs(selectedDoc.id);
    setDetailOpen(true);
  };

  // ===== 文件预览 =====
  // 由于 /files/{id}/content 需要 Bearer Token，浏览器不会为 <iframe>/<img> 自动附加
  // Authorization 头，直接用 API URL 会 401。这里先 fetch 拿到 blob 再用 blob URL 预览。
  const handlePreview = async (doc: ArchiveDoc) => {
    if (!doc.original_file_id) {
      showToast("文件不存在", "error");
      return;
    }
    // 清理上一次的 blob URL
    if (previewBlobUrlRef.current) {
      URL.revokeObjectURL(previewBlobUrlRef.current);
      previewBlobUrlRef.current = "";
    }
    try {
      const fileUrl = getFileUrl(doc.original_file_id);
      const token = localStorage.getItem("access_token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const response = await fetch(fileUrl, { headers });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      previewBlobUrlRef.current = blobUrl;
      setPreviewFileUrl(blobUrl);
      setPreviewFilename(doc.original_filename);
      setPreviewOpen(true);
    } catch (err) {
      showToast("預覽文件失敗：" + (err instanceof Error ? err.message : "未知錯誤"), "error");
    }
  };

  // ===== 关闭预览弹窗并清理 blob URL =====
  const closePreview = () => {
    if (previewBlobUrlRef.current) {
      URL.revokeObjectURL(previewBlobUrlRef.current);
      previewBlobUrlRef.current = "";
    }
    setPreviewFileUrl("");
    setPreviewOpen(false);
  };

  // ===== 在新窗口打开文件（处理认证） =====
  const openFileInNewWindow = async (fileUrl: string) => {
    try {
      const token = localStorage.getItem("access_token");
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(fileUrl, { headers });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      window.open(blobUrl, "_blank");

      setTimeout(() => {
        URL.revokeObjectURL(blobUrl);
      }, 30000);
    } catch (err) {
      showToast("打開文件失敗：" + (err instanceof Error ? err.message : "未知錯誤"), "error");
    }
  };

  // ===== 下载文件（处理认证） =====
  const downloadFile = async (fileUrl: string, filename: string) => {
    try {
      const token = localStorage.getItem("access_token");
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(fileUrl, { headers });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = filename;
      link.click();

      setTimeout(() => {
        URL.revokeObjectURL(blobUrl);
      }, 30000);
    } catch (err) {
      showToast("下載文件失敗：" + (err instanceof Error ? err.message : "未知錯誤"), "error");
    }
  };

  // ===== 应用筛选 =====
  const handleApplyFilter = async () => {
    setActionsOpen(false);
    await fetchDocs();
    showToast("篩選已套用", "info");
  };

  // ===== 导出 CSV（当前分类） =====
  const handleExport = () => {
    const tabNames: Record<string, string> = {
      all: "全部",
      needs_review: "待確認",
      confirmed: "已確認",
      archived: "已歸檔",
    };
    const headers = ["文件名", "分類", "建議檔名", "金額", "到期日", "狀態", "創建時間"];
    const rows = docs.map((d) => [
      d.original_filename,
      d.category || "",
      d.suggested_name || "",
      d.amount ? `HK$ ${d.amount}` : "",
      d.due_date || "",
      statusLabels[d.status] || d.status,
      d.created_at,
    ]);
    const csv = [headers, ...rows].map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${tabNames[activeTab]}_documents.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("清單已導出", "success");
  };

  return (
    <TommySidebarLayout>
      <PageHeader
        eyebrow="TOMMY / 文件智能歸檔"
        title="掃描件分類、命名與關鍵資料提取"
        description="上傳文件後，系統會自動 OCR、分類、建議檔名，並在人工確認後完成歸檔。"
        actions={
          <>
            <Button variant="ghost" onClick={() => setActionsOpen(true)}>更多操作</Button>
            <Button variant="primary" onClick={() => setUploadOpen(true)}>上傳文件</Button>
          </>
        }
      />

      {/* 统计卡 */}
      <div className="grid grid-cols-4 gap-2.5">
        {[
          { label: "今日上傳", value: stats?.today_upload ?? "-" },
          { label: "待確認", value: stats?.pending_review ?? "-" },
          { label: "已歸檔", value: stats?.archived ?? "-" },
          { label: "異常", value: stats?.exception ?? "-" },
        ].map((item) => (
          <div key={item.label} className="bg-white border border-[#d8dee6] rounded-lg p-3 shadow-[0_10px_30px_rgba(16,24,40,0.08)]">
            <span className="block text-[#667085] text-sm">{item.label}</span>
            <strong className="block mt-1 text-2xl">{item.value}</strong>
          </div>
        ))}
      </div>

      {/* 工作区 */}
      <div className="grid grid-cols-[minmax(560px,1fr)_minmax(380px,0.75fr)] gap-3.5 items-stretch">
        {/* 左侧：文件列表 */}
        <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-3 min-w-0">
          {/* 分类标签导航 */}
          <div className="flex justify-between items-center mb-2.5">
            <div className="flex gap-1.5">
              <button
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "all"
                    ? "bg-[#102a2f] text-white"
                    : "bg-[#f1f5f8] text-[#667085] hover:bg-[#e2e8f0]"
                )}
                onClick={() => handleTabChange("all")}
              >
                全部 ({stats?.total ?? docs.length})
              </button>
              <button
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "needs_review"
                    ? "bg-[#f59e0b] text-white"
                    : "bg-[#fef3c7] text-[#92400e] hover:bg-[#fde68a]"
                )}
                onClick={() => handleTabChange("needs_review")}
              >
                待確認 ({stats?.pending_review ?? "-"})
              </button>
              <button
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "confirmed"
                    ? "bg-[#3b82f6] text-white"
                    : "bg-[#dbeafe] text-[#1d4ed8] hover:bg-[#bfdbfe]"
                )}
                onClick={() => handleTabChange("confirmed")}
              >
                已確認 ({stats?.confirmed ?? "-"})
              </button>
              <button
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                  activeTab === "archived"
                    ? "bg-[#10b981] text-white"
                    : "bg-[#dcfce7] text-[#166534] hover:bg-[#bbf7d0]"
                )}
                onClick={() => handleTabChange("archived")}
              >
                已歸檔 ({stats?.archived ?? "-"})
              </button>
            </div>
            <Button variant="small" onClick={handleExport}>導出清單</Button>
          </div>

          <div className="flex justify-between items-center gap-2.5 mb-2.5">
            <p className="text-[#667085] text-sm">{docs.length} 份文件</p>
            <div className="flex gap-2">
              {selectedIds.size > 0 && (
                <span className="text-[#23675f] text-sm font-bold self-center">
                  已選 {selectedIds.size} 份
                </span>
              )}
              <Button variant="small" onClick={() => { fetchDocs(); fetchStats(); }}>刷新</Button>
            </div>
          </div>

          {/* 批量操作栏 */}
          {selectedIds.size > 0 && (
            <div className="flex gap-2 mb-2.5 p-2.5 bg-[#eef7f5] border border-[#23675f] rounded-lg items-center flex-wrap">
              <span className="text-sm font-bold text-[#102a2f]">批量操作 ({selectedIds.size}):</span>
              <Button variant="small-primary" onClick={handleBatchConfirm} disabled={batchOperating}>批量確認</Button>
              <Button variant="small" onClick={handleBatchArchive} disabled={batchOperating}>批量歸檔</Button>
              <Button variant="small-danger" onClick={handleBatchRetry} disabled={batchOperating}>批量重試</Button>
              <Button variant="small-ghost" onClick={() => setSelectedIds(new Set())}>取消選擇</Button>
            </div>
          )}

          {loading ? (
            <div className="text-center py-8 text-[#667085]">載入中...</div>
          ) : docs.length === 0 ? (
            <div className="text-center py-12 text-[#667085]">
              <p className="text-lg">暫無文件</p>
              <p className="text-sm mt-1">點擊「上傳文件」開始使用</p>
            </div>
          ) : (
            <>
              <div className="overflow-auto">
                <table className="w-full border-collapse min-w-0 table-fixed">
                  <thead>
                    <tr>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-center p-2 border-b border-[#d8dee6]" style={{ width: "4%" }}>
                        <input type="checkbox" className="w-3.5 h-3.5" checked={docs.length > 0 && selectedIds.size === docs.length} onChange={toggleSelectAll} />
                      </th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "18%" }}>文件名</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "9%" }}>分類</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "25%" }}>建議新檔名</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "9%" }}>金額</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "9%" }}>到期日</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "8%" }}>狀態</th>
                      <th className="text-[#344054] bg-[#f8fafc] text-xs text-left p-2 border-b border-[#d8dee6]" style={{ width: "18%" }}>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docs.map((doc) => (
                      <tr
                        key={doc.id}
                        className={`cursor-pointer ${selectedDoc?.id === doc.id ? "bg-[#eef7f5]" : "bg-white"}`}
                        onClick={() => handleSelectDoc(doc)}
                      >
                        <td className="p-2 text-sm border-b border-[#d8dee6] text-center" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            className="w-3.5 h-3.5"
                            checked={selectedIds.has(doc.id)}
                            onChange={() => toggleSelect(doc.id)}
                          />
                        </td>
                        <td className="p-2 text-sm border-b border-[#d8dee6] break-words">{doc.original_filename}</td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">
                          {doc.category && <CategoryPill category={doc.category} />}
                        </td>
                        <td className="p-2 text-sm border-b border-[#d8dee6] break-words">{doc.suggested_name || "-"}</td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">{doc.amount ? `HK$ ${Number(doc.amount).toLocaleString()}` : "-"}</td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">{doc.due_date || "-"}</td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]">
                          <StatusPill status={doc.status} label={statusLabels[doc.status]} />
                        </td>
                        <td className="p-2 text-sm border-b border-[#d8dee6]" onClick={(e) => e.stopPropagation()}>
                          <div className="flex gap-1 flex-wrap">
                            <Button variant="small" onClick={() => handlePreview(doc)}>預覽</Button>
                            {doc.status === "needs_review" && <Button variant="small-primary" onClick={() => handleSelectDoc(doc)}>確認</Button>}
                            {doc.status === "confirmed" && (
                              <>
                                <Button variant="small" onClick={handleArchive}>歸檔</Button>
                                <Button variant="small-danger" onClick={() => handleUndoArchive(doc.id)}>撤銷</Button>
                              </>
                            )}
                            {doc.status === "archived" && (
                              <>
                                <Button variant="small" onClick={handleOpenDetail}>查看</Button>
                                <Button variant="small-danger" onClick={() => handleUndoArchive(doc.id)}>撤銷</Button>
                              </>
                            )}
                            {doc.status === "exception" && (
                              <>
                                <Button variant="small-primary" onClick={() => handleRetry(doc.id)}>重試</Button>
                                <Button variant="small" onClick={handleRunOcr}>OCR</Button>
                              </>
                            )}
                            <Button variant="small-ghost" onClick={() => handleDelete(doc.id)}>刪除</Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <Pagination
                page={page}
                pageSize={pageSize}
                total={total}
                onPageChange={(p) => { setPage(p); fetchDocs(p, pageSize); }}
                onPageSizeChange={(ps) => { setPageSize(ps); setPage(1); fetchDocs(1, ps); }}
              />
            </>
          )}
        </section>

        {/* 右侧：预览 + 确认面板 */}
        {selectedDoc ? (
          <aside className="grid gap-2.5">
            {/* 文件预览 / OCR 原文 */}
            <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-3 min-w-0">
              <div className="flex justify-between items-center gap-2.5 mb-2.5">
                <h3 className="text-base font-bold">文件預覽 / OCR 原文</h3>
                <StatusPill status={selectedDoc.status} label={statusLabels[selectedDoc.status]} />
              </div>
              <div className="border border-[#d8dee6] bg-[#f1f5f8] rounded-lg p-2.5 grid grid-cols-[86px_1fr] gap-2.5 items-center">
                <div className="w-[74px] h-[58px] border border-[#cbd5e1] bg-white rounded-md p-2 grid gap-1.5">
                  <div className="h-[5px] bg-[#d8dee6] rounded-full" />
                  <div className="h-[5px] bg-[#d8dee6] rounded-full w-[65%]" />
                  <div className="h-[5px] bg-[#d8dee6] rounded-full" />
                </div>
                <div className="min-w-0 grid gap-1">
                  <strong className="break-words">{selectedDoc.original_filename}</strong>
                  <span className="text-[#667085] text-sm">創建於 {selectedDoc.created_at.slice(0, 19).replace("T", " ")}</span>
                  <span className="text-[#667085] text-sm">
                    {selectedDoc.confidence ? `AI 信心：${selectedDoc.confidence === "medium" ? "中" : selectedDoc.confidence === "high" ? "高" : "低"}` : ""}
                  </span>
                </div>
              </div>
              <div className="border border-[#d8dee6] bg-[#f1f5f8] rounded-lg p-2.5 text-[#344054] leading-relaxed whitespace-pre-wrap max-h-[360px] overflow-auto text-sm mt-2">
                {selectedDoc.ocr_text || "（無 OCR 文本）"}
              </div>
            </section>

            {/* AI 分类结果确认面板 */}
            <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-3 grid gap-2.5 min-w-0">
              <div className="flex justify-between items-center gap-2.5">
                <h3 className="text-base font-bold">AI 分類結果確認</h3>
                <div className="flex gap-1">
                  <Button variant="small" onClick={handleRunOcr}>重新OCR</Button>
                  <Button variant="small" onClick={handleOpenDetail}>查看詳情</Button>
                </div>
              </div>

              {/* 置信度提示 */}
              {selectedDoc.confidence && (
                <div className="grid grid-cols-[1fr_auto] gap-2 items-center p-2.5 border border-[#fedf89] bg-[#fffaeb] rounded-lg">
                  <div>
                    <strong>AI 信心：{selectedDoc.confidence === "medium" ? "中" : selectedDoc.confidence === "high" ? "高" : "低"}</strong>
                    <div className="text-[#667085] text-xs mt-0.5">
                      {selectedDoc.confidence === "low" ? "AI 信心較低，請仔細核對各項資料。" : "偵測到金額及日期，但仍需人工確認。"}
                    </div>
                  </div>
                  <StatusPill status={selectedDoc.status} label={statusLabels[selectedDoc.status]} />
                </div>
              )}

              {/* 编辑字段 */}
              <div className="grid gap-2.5">
                <div className="grid gap-1">
                  <label className="text-[#344054] font-bold text-sm">分類</label>
                  <select
                    className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white text-[#1d2939]"
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                  >
                    <option>租務</option>
                    <option>財務</option>
                    <option>人事</option>
                    <option>教育局通告</option>
                    <option>會議</option>
                    <option>其他</option>
                  </select>
                  <span className="text-[#667085] text-xs">來源：AI 分類</span>
                </div>

                <div className="grid gap-1">
                  <label className="text-[#344054] font-bold text-sm">建議檔名</label>
                  <input
                    className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white text-[#1d2939]"
                    value={editFilename}
                    onChange={(e) => setEditFilename(e.target.value)}
                  />
                  <span className="text-[#667085] text-xs">格式：YYYY-MM-DD_類別_標題</span>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div className="grid gap-1">
                    <label className="text-[#344054] font-bold text-sm">金額</label>
                    <input
                      className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white text-[#1d2939]"
                      value={editAmount}
                      onChange={(e) => setEditAmount(e.target.value)}
                      placeholder="HK$"
                    />
                  </div>

                  <div className="grid gap-1">
                    <label className="text-[#344054] font-bold text-sm">到期日</label>
                    <input
                      type="date"
                      className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white text-[#1d2939]"
                      value={editDueDate}
                      onChange={(e) => setEditDate(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="flex gap-2 items-center flex-wrap">
                <Button variant="primary" onClick={handleConfirm}>確認保存</Button>
                <Button variant="default" onClick={handleArchive}>確認並歸檔</Button>
                <Button variant="ghost" onClick={handleFlagException}>標記異常</Button>
              </div>
            </section>
          </aside>
        ) : (
          <aside className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-6 text-center text-[#667085]">
            <p>請從左側列表選擇一份文件查看詳情</p>
          </aside>
        )}
      </div>

      {/* 上传弹窗 */}
      <Modal open={uploadOpen} onClose={() => setUploadOpen(false)} title="上傳文件" description="支持 PDF、JPG、PNG 等格式，上傳後自動 OCR 及 AI 分類。" width="560px">
        <UploadDropzone
          onUploadSuccess={handleUploadSuccess}
          onUploadError={(err) => showToast(err, "error")}
          autoCreateArchive={true}
        />
      </Modal>

      {/* 更多操作弹窗 */}
      <Modal open={actionsOpen} onClose={() => setActionsOpen(false)} title="更多操作" description="搜索、篩選、批量 OCR 及導出功能。">
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2 grid gap-1">
            <label className="text-[#344054] font-bold text-sm">搜尋文件</label>
            <input
              className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white"
              placeholder="搜尋文件名、分類、金額、日期或 OCR 原文內容"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="grid gap-1">
            <label className="text-[#344054] font-bold text-sm">分類</label>
            <select
              className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white"
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
            >
              <option value="">全部分類</option>
              <option>財務</option>
              <option>人事</option>
              <option>租務</option>
              <option>教育局通告</option>
              <option>會議</option>
              <option>其他</option>
            </select>
          </div>
          <div className="grid gap-1">
            <label className="text-[#344054] font-bold text-sm">狀態</label>
            <select
              className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">全部狀態</option>
              <option value="needs_review">待確認</option>
              <option value="confirmed">已確認</option>
              <option value="archived">已歸檔</option>
              <option value="exception">異常</option>
            </select>
          </div>
          <div className="col-span-2 grid grid-cols-2 gap-3">
            <div className="grid gap-1">
              <label className="text-[#344054] font-bold text-sm">日期從</label>
              <input type="date" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <label className="text-[#344054] font-bold text-sm">日期至</label>
              <input type="date" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </div>
          </div>
          <div className="col-span-2 flex gap-2">
            <Button variant="primary" onClick={handleApplyFilter}>套用篩選</Button>
            <Button variant="ghost" onClick={() => { setSearchQuery(""); setFilterCategory(""); setFilterStatus(""); setDateFrom(""); setDateTo(""); }}>清除篩選</Button>
            <Button variant="default" onClick={handleExport}>導出清單</Button>
          </div>
        </div>
      </Modal>

      {/* 详情弹窗 */}
      <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title="文件詳情" description="摘要、AI 來源和審計記錄。">
        {selectedDoc && (
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 grid gap-1">
              <label className="text-[#344054] font-bold text-sm">摘要</label>
              <textarea className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-[#f1f5f8] min-h-[78px] resize-y" readOnly value={selectedDoc.ai_summary || ""} />
            </div>
            <div className="col-span-2">
              <h3 className="text-base font-bold mb-2">審計記錄</h3>
              {auditLogs.length === 0 ? (
                <p className="text-[#667085] text-sm">暫無審計記錄</p>
              ) : (
                <ul className="grid gap-1.5 list-none m-0 p-0">
                  {auditLogs.map((log) => (
                    <li key={log.id} className="pl-2.5 border-l-[3px] border-[#d8dee6] text-[#667085] text-xs leading-snug">
                      {log.created_at.slice(11, 19)} {log.user_name || "系統"} - {log.detail || log.action}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {(selectedDoc.status === "confirmed" || selectedDoc.status === "archived") && (
              <div className="col-span-2 flex justify-end gap-2">
                <Button variant="small-danger" onClick={() => { handleUndoArchive(selectedDoc.id); setDetailOpen(false); }}>
                  {selectedDoc.status === "archived" ? "撤銷歸檔" : "撤銷確認"}
                </Button>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* 文件预览弹窗 */}
      <Modal open={previewOpen} onClose={closePreview} title="文件預覽" description={previewFilename} width="800px">
        <div className="flex flex-col h-[500px]">
          <div className="flex gap-2 mb-3">
            <Button variant="small" onClick={() => openFileInNewWindow(previewFileUrl)}>在新窗口打開</Button>
            <Button variant="small" onClick={() => downloadFile(previewFileUrl, previewFilename)}>下載文件</Button>
          </div>
          <div className="flex-1 bg-[#f1f5f8] rounded-lg overflow-auto border border-[#d8dee6] flex items-center justify-center">
            {previewFilename.match(/\.(pdf)$/i) ? (
              <iframe
                src={previewFileUrl}
                className="w-full h-full min-h-[450px]"
                title="PDF Preview"
              />
            ) : previewFilename.match(/\.(jpg|jpeg|png|gif|bmp|webp|svg|tiff?)$/i) ? (
              <img
                src={previewFileUrl}
                alt={previewFilename}
                className="max-w-full max-h-full object-contain"
                onError={() => {
                  const el = document.getElementById("preview-img-fallback");
                  if (el) el.style.display = "flex";
                }}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-[#667085]">
                <div className="text-center">
                  <p className="text-lg mb-2">文件預覽</p>
                  <p className="text-sm">此格式不支援內嵌預覽</p>
                  <p className="text-xs mt-1 text-[#999]">點擊上方按鈕在新窗口打開或下載</p>
                </div>
              </div>
            )}
            <div id="preview-img-fallback" className="hidden flex-col items-center justify-center text-[#667085] absolute inset-0">
              <p className="text-lg mb-2">圖片載入失敗</p>
              <p className="text-sm">請點擊上方按鈕在新窗口打開</p>
            </div>
          </div>
        </div>
      </Modal>
    </TommySidebarLayout>
  );
}

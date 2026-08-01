/**
 * Tommy 個人設定頁 - 用戶信息 + 修改密碼
 */
"use client";

import { useState, useEffect } from "react";
import { TommySidebarLayout } from "@/components/modules/tommy/TommySidebarLayout";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/shared/Button";
import { useToast } from "@/components/shared/Toast";
import { apiFetch, getUserInfo } from "@/lib/api";

export default function TommySettingsPage() {
  const { showToast } = useToast();
  const [userInfo, setUserInfo] = useState<{ username: string; full_name?: string; roles: string[] } | null>(null);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  useEffect(() => {
    const info = getUserInfo();
    if (info) {
      setUserInfo({ username: info.username, full_name: info.full_name, roles: info.roles });
    }
  }, []);

  const [changingPassword, setChangingPassword] = useState(false);

  const handleChangePassword = async () => {
    if (!oldPassword || !newPassword || !confirmPassword) {
      showToast("請填寫所有密碼欄位", "warning");
      return;
    }
    if (newPassword !== confirmPassword) {
      showToast("新密碼與確認密碼不一致", "error");
      return;
    }
    if (newPassword.length < 6) {
      showToast("新密碼長度至少 6 位", "warning");
      return;
    }
    setChangingPassword(true);
    try {
      await apiFetch("/accounts/change-password", {
        method: "POST",
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      });
      showToast("密碼修改成功", "success");
      setOldPassword(""); setNewPassword(""); setConfirmPassword("");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "修改失敗", "error");
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <TommySidebarLayout>
      <PageHeader eyebrow="TOMMY / 個人設定" title="個人設定" description="查看帳號資訊及修改密碼。" />

      <div className="grid gap-3 max-w-2xl">
        {/* 帳號資訊 */}
        <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-4">
          <h3 className="text-base font-bold mb-3">帳號資訊</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[#667085] text-sm">用戶名</label>
              <p className="font-bold">{userInfo?.username || "-"}</p>
            </div>
            <div>
              <label className="text-[#667085] text-sm">姓名</label>
              <p className="font-bold">{userInfo?.full_name || "-"}</p>
            </div>
            <div>
              <label className="text-[#667085] text-sm">角色</label>
              <p className="font-bold">{userInfo?.roles?.join(", ") || "-"}</p>
            </div>
          </div>
        </section>

        {/* 修改密碼 */}
        <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-4">
          <h3 className="text-base font-bold mb-3">修改密碼</h3>
          <div className="grid gap-3">
            <div className="grid gap-1">
              <label className="text-[#344054] font-bold text-sm">目前密碼</label>
              <input type="password" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <label className="text-[#344054] font-bold text-sm">新密碼</label>
              <input type="password" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <label className="text-[#344054] font-bold text-sm">確認新密碼</label>
              <input type="password" className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
            </div>
            <div>
              <Button variant="primary" onClick={handleChangePassword} disabled={changingPassword}>{changingPassword ? "修改中..." : "確認修改"}</Button>
            </div>
          </div>
        </section>

        {/* 系統偏好 */}
        <section className="bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-4">
          <h3 className="text-base font-bold mb-3">系統偏好</h3>
          <div className="grid gap-3">
            <label className="flex items-center gap-2">
              <input type="checkbox" defaultChecked className="w-4 h-4" />
              <span className="text-sm">文件歸檔後自動發送通知</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" defaultChecked className="w-4 h-4" />
              <span className="text-sm">租約到期前 30 天自動提醒</span>
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" className="w-4 h-4" />
              <span className="text-sm">繳費日前 3 天自動提醒租戶</span>
            </label>
          </div>
        </section>
      </div>
    </TommySidebarLayout>
  );
}

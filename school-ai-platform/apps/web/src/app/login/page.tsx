/**
 * 登录页 - 调用后端 /accounts/login API
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, setToken, setUserInfo } from "@/lib/api";
import { Button } from "@/components/shared/Button";
import { useToast } from "@/components/shared/Toast";

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    username: string;
    full_name?: string;
    roles: string[];
  };
}

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { showToast } = useToast();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const result = await apiFetch<LoginResponse>("/accounts/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });

      setToken(result.access_token);
      setUserInfo({
        id: result.user.id,
        username: result.user.username,
        roles: result.user.roles,
        full_name: result.user.full_name,
      });

      showToast("登入成功", "success");

      // 根据角色跳转
      const role = result.user.roles[0];
      router.push(`/dashboard/${role}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "登入失敗";
      showToast(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f6f7f9] flex items-center justify-center p-4">
      <div className="w-[min(440px,100%)] bg-white border border-[#d8dee6] rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 grid place-items-center bg-[#d9ebe7] text-[#123a36] rounded-lg font-bold text-xl">
            PY
          </div>
          <div>
            <h1 className="text-xl font-bold">培英 AI 行政平台</h1>
            <p className="text-[#667085] text-sm">Pui Ying AI Administration Platform</p>
          </div>
        </div>

        <form onSubmit={handleLogin} className="grid gap-4">
          <div className="grid gap-1">
            <label className="text-[#344054] font-bold text-sm">用戶名</label>
            <input
              className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white text-[#1d2939] focus:outline-none focus:border-[#23675f]"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="輸入用戶名"
              disabled={loading}
            />
          </div>

          <div className="grid gap-1">
            <label className="text-[#344054] font-bold text-sm">密碼</label>
            <input
              type="password"
              className="w-full border border-[#d8dee6] rounded-lg px-2.5 py-2 bg-white text-[#1d2939] focus:outline-none focus:border-[#23675f]"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="輸入密碼"
              disabled={loading}
            />
          </div>

          <Button variant="primary" className="w-full justify-center" disabled={loading}>
            {loading ? "登入中..." : "登入"}
          </Button>

          <div className="text-center text-[#667085] text-xs">
            測試帳號：tommy / tommy123 或 admin / admin123
          </div>
        </form>
      </div>
    </div>
  );
}

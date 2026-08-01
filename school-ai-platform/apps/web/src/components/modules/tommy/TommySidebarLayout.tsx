/**
 * Tommy Dashboard 布局 - 包含侧边栏
 */
"use client";

import { clsx } from "clsx";
import { usePathname, useRouter } from "next/navigation";
import { Settings } from "lucide-react";
import { getUserInfo, clearToken } from "@/lib/api";

const navItems = [
  { label: "總覽", path: "/dashboard/tommy" },
  { label: "文件歸檔", path: "/dashboard/tommy/archive" },
  { label: "租務提醒", path: "/dashboard/tommy/rental" },
];

export function TommySidebarLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const user = getUserInfo();

  const handleLogout = () => {
    clearToken();
    router.push("/login");
  };

  return (
    <div className="min-h-screen overflow-hidden">
      {/* 侧边栏 - 固定定位 */}
      <aside className="fixed left-0 top-0 w-[224px] h-screen bg-[#102a2f] text-[#eef7f5] p-4 flex flex-col gap-4 z-50">
        {/* 品牌区 */}
        <div className="grid grid-cols-[40px_1fr] gap-2.5 items-center">
          <div className="w-10 h-10 grid place-items-center bg-[#d9ebe7] text-[#123a36] rounded-lg font-bold text-lg">
            PY
          </div>
          <div>
            <h1 className="text-base font-bold mb-0.5 leading-tight">培英 AI 行政平台</h1>
            <p className="text-[#a7c3bd] text-xs">Tommy 專屬工作台</p>
          </div>
        </div>

        {/* 导航列表 */}
        <nav className="grid gap-1.5">
          {navItems.map((item) => (
            <button
              key={item.path}
              className={clsx(
                "text-left px-3 py-2.5 rounded-lg border-0 cursor-pointer transition-colors",
                pathname === item.path
                  ? "text-white bg-white/12"
                  : "text-[#dcecea] bg-transparent hover:text-white hover:bg-white/12"
              )}
              onClick={() => router.push(item.path)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* 底部区域 */}
        <div className="mt-auto flex flex-col gap-3">
          {/* 身份提示 */}
          <div className="p-3 bg-white/8 border border-white/12 rounded-lg grid gap-2 leading-relaxed">
            <strong>目前身份：Tommy</strong>
            <span className="text-[#a7c3bd] text-xs">
              只顯示已授權的文件歸檔與租務提醒功能。
            </span>
          </div>

          {/* 设置图标和退出 */}
          <div className="flex gap-2 items-center">
            <button
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-[#a7c3bd] bg-transparent hover:text-white hover:bg-white/12 cursor-pointer border-0 transition-colors"
              onClick={() => router.push("/dashboard/tommy/settings")}
              title="個人設定"
            >
              <Settings size={16} />
            </button>
            <button
              className="flex-1 text-left px-3 py-2 rounded-lg text-[#a7c3bd] bg-transparent hover:text-white hover:bg-white/12 cursor-pointer border-0 transition-colors"
              onClick={handleLogout}
              title="退出登入"
            >
              退出
            </button>
          </div>
        </div>
      </aside>

      {/* 主内容区 - 可滚动 */}
      <main className="ml-[224px] p-4 grid gap-3.5 overflow-y-auto h-screen">{children}</main>
    </div>
  );
}

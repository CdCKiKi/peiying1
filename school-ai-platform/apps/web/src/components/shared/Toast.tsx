/**
 * Toast 通知组件 - 全局通知反馈
 */
"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Fallback: 如果不在 Provider 内，返回 noop
    return { showToast: () => {} };
  }
  return ctx;
}

let toastId = 0;

const typeStyles: Record<ToastType, string> = {
  success: "bg-[#027a48] text-white",
  error: "bg-[#b42318] text-white",
  warning: "bg-[#936a00] text-white",
  info: "bg-[#102a2f] text-white",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = ++toastId;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast 容器 */}
      <div className="fixed right-6 bottom-6 z-50 flex flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`px-4 py-3 rounded-lg shadow-[0_10px_30px_rgba(16,24,40,0.08)] text-sm font-bold transition-all duration-300 ${typeStyles[toast.type]}`}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

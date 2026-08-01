/**
 * 通用 Modal 弹窗组件
 */
"use client";

import { ReactNode } from "react";
import { Button } from "./Button";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  width?: string;
}

export function Modal({ open, onClose, title, description, children, width = "680px" }: ModalProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-30 flex items-center justify-center p-4 bg-[rgba(16,24,40,0.45)]"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <section
        className="bg-white rounded-lg border border-[#d8dee6] shadow-[0_10px_30px_rgba(16,24,40,0.08)] p-4 overflow-auto max-h-[calc(100vh-48px)]"
        style={{ width: `min(${width}, 100%)` }}
      >
        <div className="flex justify-between items-center gap-2.5 mb-3">
          <div>
            <h3 className="text-base font-bold">{title}</h3>
            {description && <p className="text-[#667085] text-sm">{description}</p>}
          </div>
          <Button variant="small-ghost" onClick={onClose}>關閉</Button>
        </div>
        {children}
      </section>
    </div>
  );
}

/**
 * 文件上传组件 - 支持拖拽和点击上传
 */
"use client";

import { useState, useRef, DragEvent, ChangeEvent } from "react";
import { apiUpload } from "@/lib/api";

interface UploadDropzoneProps {
  /** 上传成功回调 */
  onUploadSuccess: (fileId: string, filename: string) => void;
  /** 上传失败回调 */
  onUploadError?: (error: string) => void;
  /** 接受的文件类型 */
  accept?: string;
  /** 上传后的 API 路径（上传文件后自动调用） */
  autoCreateArchive?: boolean;
}

export function UploadDropzone({
  onUploadSuccess,
  onUploadError,
  accept = ".pdf,.jpg,.jpeg,.png,.gif,.bmp,.tiff",
  autoCreateArchive = false,
}: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadProgress("正在上傳...");

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgress(`正在上傳 ${file.name} (${i + 1}/${files.length})...`);

        // 上传文件
        const result = await apiUpload<{ id: string; original_filename: string }>(
          "/files/upload",
          file
        );

        // 如果需要自动创建归档文档
        if (autoCreateArchive) {
          setUploadProgress(`正在處理 ${file.name}...`);
          await fetch("http://localhost:8000/api/v1/tommy/archive-documents", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ original_file_id: result.id }),
          });
        }

        onUploadSuccess(result.id, result.original_filename);
      }
      setUploadProgress("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "上傳失敗";
      onUploadError?.(msg);
      setUploadProgress("");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
  };

  return (
    <div
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        isDragging
          ? "border-[#23675f] bg-[#eef7f5]"
          : "border-[#d8dee6] bg-[#f1f5f8] hover:border-[#23675f]"
      } ${uploading ? "pointer-events-none opacity-60" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        multiple
        className="hidden"
        onChange={handleChange}
      />
      {uploading ? (
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-3 border-[#23675f] border-t-transparent rounded-full animate-spin" />
          <p className="text-[#23675f] font-bold text-sm">{uploadProgress || "處理中..."}</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-full bg-[#d9ebe7] flex items-center justify-center text-2xl">
            📁
          </div>
          <p className="font-bold text-[#1d2939]">拖拽文件到此處或點擊上傳</p>
          <p className="text-[#667085] text-sm">支持 PDF、JPG、PNG 等格式，單個文件最大 50MB</p>
        </div>
      )}
    </div>
  );
}

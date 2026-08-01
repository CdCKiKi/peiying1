/**
 * 文件上传组件 - 支持拖拽和点击上传，批量选择后可移除，点击确定后上传
 */
"use client";

import { useState, useRef, DragEvent, ChangeEvent } from "react";
import { apiFetch, apiUpload } from "@/lib/api";

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
  accept = ".pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.bmp,.tiff",
  autoCreateArchive = false,
}: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>("");
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const newFiles = Array.from(files);
    setPendingFiles((prev) => [...prev, ...newFiles]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const removeFile = (index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const clearFiles = () => {
    setPendingFiles([]);
  };

  const handleConfirmUpload = async () => {
    if (pendingFiles.length === 0) return;

    setUploading(true);
    setUploadProgress("正在上傳...");

    try {
      for (let i = 0; i < pendingFiles.length; i++) {
        const file = pendingFiles[i];
        setUploadProgress(`正在上傳 ${file.name} (${i + 1}/${pendingFiles.length})...`);

        // 上传文件
        const result = await apiUpload<{ id: string; original_filename: string }>(
          "/files/upload",
          file
        );

        // 如果需要自动创建归档文档
        if (autoCreateArchive) {
          setUploadProgress(`正在處理 ${file.name}...`);
          await apiFetch("/tommy/archive-documents", {
            method: "POST",
            body: JSON.stringify({ original_file_id: result.id }),
          });
        }

        onUploadSuccess(result.id, result.original_filename);
      }
      setUploadProgress("");
      setPendingFiles([]);
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
    addFiles(e.dataTransfer.files);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    addFiles(e.target.files);
  };

  return (
    <div className="grid gap-3">
      {/* 拖拽区域 */}
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
            <p className="text-[#667085] text-sm">支持 PDF、Word、JPG、PNG 等格式，單個文件最大 50MB</p>
          </div>
        )}
      </div>

      {/* 待上传文件列表 */}
      {!uploading && pendingFiles.length > 0 && (
        <div className="border border-[#d8dee6] rounded-lg p-3 bg-white">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-bold text-[#1d2939]">待上傳文件 ({pendingFiles.length})</span>
            <button
              className="text-xs text-[#667085] hover:text-[#dc2626] transition-colors"
              onClick={clearFiles}
            >
              全部清除
            </button>
          </div>
          <ul className="grid gap-1.5 max-h-[200px] overflow-auto">
            {pendingFiles.map((file, index) => (
              <li
                key={`${file.name}-${index}`}
                className="flex justify-between items-center gap-2 px-2.5 py-1.5 bg-[#f8fafc] rounded-md text-sm"
              >
                <span className="truncate text-[#344054]" title={file.name}>
                  {file.name}
                </span>
                <span className="text-[#667085] text-xs shrink-0">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </span>
                <button
                  className="text-[#667085] hover:text-[#dc2626] transition-colors shrink-0 ml-1"
                  onClick={() => removeFile(index)}
                  title="移除"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
          <button
            className="mt-3 w-full bg-[#23675f] text-white font-bold py-2 rounded-lg hover:bg-[#1a4f48] transition-colors text-sm"
            onClick={handleConfirmUpload}
          >
            確定上傳
          </button>
        </div>
      )}
    </div>
  );
}

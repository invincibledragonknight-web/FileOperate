"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Button } from "@/components/ui/button";
import {
  CheckCircle2,
  FolderDown,
  Loader2,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type UploadItem = {
  name: string;
  size: number;
  modified?: string;
  url?: string;
};

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes)) return "0 B";
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1
  );
  const value = bytes / 1024 ** exponent;
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${
    units[exponent]
  }`;
}

function formatDate(value?: string) {
  if (!value) return "Just now";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Just now";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function toTimestamp(value?: string) {
  const time = new Date(value ?? "").getTime();
  return Number.isNaN(time) ? 0 : time;
}

export function UploadManager() {
  const [files, setFiles] = useState<UploadItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const sortedFiles = useMemo(
    () =>
      [...files].sort(
        (a, b) => toTimestamp(b.modified) - toTimestamp(a.modified)
      ),
    [files]
  );

  const fetchFiles = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/uploads", { cache: "no-store" });
      if (!response.ok) {
        throw new Error("Unable to load uploaded files");
      }
      const data = await response.json();
      setFiles(Array.isArray(data.files) ? data.files : []);
    } catch (error: any) {
      toast.error(error?.message || "Failed to load uploaded files");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleUpload = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList?.length) return;
      setIsUploading(true);
      try {
        for (const file of Array.from(fileList)) {
          const formData = new FormData();
          formData.append("file", file);

          const response = await fetch("/api/uploads", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || "Failed to upload file");
          }
        }
        toast.success("Files uploaded to /public/uploads");
        await fetchFiles();
      } catch (error: any) {
        toast.error(error?.message || "Failed to upload file");
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    },
    [fetchFiles]
  );

  const handleDelete = useCallback(
    async (name: string) => {
      setIsLoading(true);
      try {
        const response = await fetch(
          `/api/uploads?file=${encodeURIComponent(name)}`,
          {
            method: "DELETE",
          }
        );
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.error || "Unable to delete file");
        }
        toast.success(`Removed ${name}`);
        await fetchFiles();
      } catch (error: any) {
        toast.error(error?.message || "Unable to delete file");
      } finally {
        setIsLoading(false);
      }
    },
    [fetchFiles]
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setDragActive(false);
      handleUpload(event.dataTransfer.files);
    },
    [handleUpload]
  );

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setDragActive(false);
    },
    []
  );

  const openFilePicker = () => fileInputRef.current?.click();

  return (
    <section className="relative overflow-hidden rounded-3xl border border-white/70 bg-gradient-to-br from-white/90 via-white/70 to-slate-50/70 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.12)] backdrop-blur-2xl">
      <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-3xl">
        <div className="absolute -left-10 -top-16 h-40 w-40 rounded-full bg-gradient-to-br from-[#dbe8ff] to-white blur-3xl" />
        <div className="absolute bottom-0 right-0 h-52 w-52 rounded-full bg-gradient-to-br from-[#d7f6ea] to-white blur-3xl" />
      </div>

      <div className="relative flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-500">
            File Vault
          </p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
            Upload and curate agent context
          </h2>
          <p className="text-sm text-slate-500">
            Files are saved to <span className="font-semibold">/public/uploads</span> so your
            agent can reuse them across threads.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchFiles}
            disabled={isLoading || isUploading}
            className="backdrop-blur"
          >
            <RefreshCw
              className={cn("h-4 w-4", isLoading ? "animate-spin" : "")}
            />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={openFilePicker}
            disabled={isUploading}
            className="rounded-full bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 px-4 text-white shadow-md hover:shadow-lg"
          >
            {isUploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {isUploading ? "Uploading" : "Add files"}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="sr-only"
            onChange={(event) => handleUpload(event.target.files)}
          />
        </div>
      </div>

      <div className="relative mt-6 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={cn(
            "group relative flex min-h-[180px] items-center justify-center rounded-2xl border border-white/70 bg-white/70 p-6 text-center shadow-inner backdrop-blur-xl transition-all",
            dragActive
              ? "border-slate-300 shadow-[0_12px_45px_rgba(59,130,246,0.25)]"
              : "hover:border-slate-200 hover:shadow-[0_14px_40px_rgba(15,23,42,0.12)]"
          )}
        >
          <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br from-white/70 via-white/40 to-white/10 opacity-90" />
          <div className="relative flex max-w-xl flex-col items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 text-white shadow-lg">
              <FolderDown className="h-5 w-5" />
            </div>
            <p className="text-base font-semibold text-slate-900">
              Drop files here or browse
            </p>
            <p className="text-sm text-slate-500">
              We keep them neatly organized in <code className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">/public/uploads</code> for quick reuse.
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={openFilePicker}
                disabled={isUploading}
                className="rounded-full border border-white/70 bg-white/80 text-slate-900 shadow-sm"
              >
                Browse files
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchFiles}
                disabled={isLoading}
                className="text-slate-600 hover:text-slate-900"
              >
                Quick sync
              </Button>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-white/70 bg-white/75 p-4 shadow-sm backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Uploaded
              </p>
              <p className="text-sm text-slate-500">
                {sortedFiles.length} file{sortedFiles.length === 1 ? "" : "s"}
              </p>
            </div>
            {isLoading && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Syncing
              </div>
            )}
          </div>

          <div className="mt-3 max-h-[240px] space-y-3 overflow-y-auto pr-1">
            {sortedFiles.length === 0 ? (
              <div className="flex h-[180px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/60 text-center text-sm text-slate-500">
                <CheckCircle2 className="mb-2 h-5 w-5 text-slate-400" />
                No uploads yet. Drop a file to get started.
              </div>
            ) : (
              sortedFiles.map((file) => (
                <div
                  key={file.name}
                  className="group flex items-center justify-between gap-3 rounded-2xl border border-white/70 bg-white/80 px-4 py-3 shadow-[0_8px_20px_rgba(15,23,42,0.08)] backdrop-blur transition hover:-translate-y-[1px] hover:shadow-[0_12px_28px_rgba(15,23,42,0.12)]"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-slate-900 to-slate-700 text-white shadow-md">
                      <FolderDown className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">
                        {file.name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {formatBytes(file.size)} • {formatDate(file.modified)}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-shrink-0 items-center gap-1.5">
                    {file.url && (
                      <Button
                        variant="ghost"
                        size="sm"
                        asChild
                        className="rounded-full text-slate-700 hover:bg-slate-100 hover:text-slate-900"
                      >
                        <a
                          href={file.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Open
                        </a>
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(file.name)}
                      disabled={isLoading || isUploading}
                      className="rounded-full border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  Folder,
  Loader2,
  RefreshCw,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

type WorkspaceNode = {
  name: string;
  path: string;
  type: "file" | "directory";
  size?: number;
  modified?: string;
  children?: WorkspaceNode[];
};

const WORKSPACE_ROOT = "/workspace";
const ROOT_KEY = "__workspace_root__";

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

function normalizeSlashes(value: string) {
  return value.replace(/\\/g, "/");
}

function trimLeadingSlashes(value: string) {
  return value.replace(/^\/+/, "");
}

function trimTrailingSlashes(value: string) {
  return value.replace(/\/+$/, "");
}

function normalizePathSegments(value: string) {
  const segments = value.split("/").filter(Boolean);
  const output: string[] = [];
  segments.forEach((segment) => {
    if (segment === ".") return;
    if (segment === "..") {
      output.pop();
      return;
    }
    output.push(segment);
  });
  return output.join("/");
}

function toWorkspaceRelativePath(value: string) {
  if (!value) return "";
  const normalized = trimTrailingSlashes(
    normalizeSlashes(value).replace(/^(\.\/)+/, "")
  );
  const lower = normalized.toLowerCase();
  const workspaceMarker = "/workspace/";
  const workspaceIndex = lower.lastIndexOf(workspaceMarker);
  if (workspaceIndex >= 0) {
    return normalizePathSegments(
      trimLeadingSlashes(normalized.slice(workspaceIndex + workspaceMarker.length))
    );
  }
  if (lower.endsWith("/workspace")) {
    return "";
  }
  const trimmed = trimLeadingSlashes(normalized);
  if (!trimmed || trimmed.toLowerCase() === "workspace") return "";
  if (trimmed.toLowerCase().startsWith("workspace/")) {
    return normalizePathSegments(trimmed.slice("workspace/".length));
  }
  return normalizePathSegments(trimmed);
}

function buildWorkspacePath(value: string) {
  const relative = toWorkspaceRelativePath(value);
  return relative ? `${WORKSPACE_ROOT}/${relative}` : WORKSPACE_ROOT;
}

function buildWorkspaceDisplayPath(value: string) {
  const relative = toWorkspaceRelativePath(value);
  return relative ? `workspace/${relative}` : "workspace";
}

function getNodeKey(value: string) {
  const relative = toWorkspaceRelativePath(value);
  return relative || ROOT_KEY;
}

function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

function parseContentDispositionFilename(header: string | null) {
  if (!header) return null;
  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  const asciiMatch = /filename=\"?([^\";]+)\"?/i.exec(header);
  return asciiMatch?.[1] || null;
}

export function WorkspacePanel() {
  const [open, setOpen] = useState(false);
  const [tree, setTree] = useState<WorkspaceNode | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set([ROOT_KEY])
  );
  const [downloadingKeys, setDownloadingKeys] = useState<Set<string>>(
    () => new Set()
  );
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const fetchTree = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/workspace", { cache: "no-store" });
      if (!response.ok) {
        throw new Error("Unable to load workspace files");
      }
      const data = await response.json();
      setTree(data?.tree ?? null);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "Failed to load workspace files"));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      fetchTree();
    }
  }, [open, fetchTree]);

  const toggleExpanded = useCallback((key: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  const handleUpload = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList?.length) return;
      setIsUploading(true);
      try {
        for (const file of fileList) {
          const formData = new FormData();
          formData.append("file", file);
          const response = await fetch("/api/workspace", {
            method: "POST",
            body: formData,
          });
          if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || "Failed to upload file");
          }
        }
        toast.success(
          `Uploaded ${fileList.length} file${fileList.length === 1 ? "" : "s"}`
        );
        await fetchTree();
      } catch (error: unknown) {
        toast.error(getErrorMessage(error, "Failed to upload file"));
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    },
    [fetchTree]
  );

  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleDragOver = useCallback(
    (event: React.DragEvent<HTMLButtonElement>) => {
      event.preventDefault();
      if (isUploading) return;
      event.dataTransfer.dropEffect = "copy";
      setIsDragging(true);
    },
    [isUploading]
  );

  const handleDragLeave = useCallback(
    (event: React.DragEvent<HTMLButtonElement>) => {
      const related = event.relatedTarget;
      if (related && event.currentTarget.contains(related as Node)) {
        return;
      }
      setIsDragging(false);
    },
    []
  );

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLButtonElement>) => {
      event.preventDefault();
      setIsDragging(false);
      if (isUploading) return;
      handleUpload(event.dataTransfer.files);
    },
    [handleUpload, isUploading]
  );

  const treeStats = useMemo(() => {
    if (!tree) {
      return { files: 0, directories: 0 };
    }

    const walk = (node: WorkspaceNode, isRoot: boolean) => {
      if (node.type === "file") {
        return { files: 1, directories: 0 };
      }

      let files = 0;
      let directories = isRoot ? 0 : 1;

      node.children?.forEach((child) => {
        const counts = walk(child, false);
        files += counts.files;
        directories += counts.directories;
      });

      return { files, directories };
    };

    return walk(tree, true);
  }, [tree]);

  const treeSummary = tree
    ? `${treeStats.files} file${treeStats.files === 1 ? "" : "s"} - ${
        treeStats.directories
      } folder${treeStats.directories === 1 ? "" : "s"}`
    : isLoading
      ? "Loading workspace tree..."
      : "Workspace data unavailable.";

  const expandAll = useCallback(() => {
    if (!tree) return;
    const next = new Set<string>();
    const visit = (node: WorkspaceNode) => {
      if (node.type === "directory") {
        next.add(getNodeKey(node.path));
        node.children?.forEach(visit);
      }
    };
    visit(tree);
    setExpanded(next);
  }, [tree]);

  const collapseAll = useCallback(() => {
    setExpanded(new Set([ROOT_KEY]));
  }, []);

  const handleDownload = useCallback(async (node: WorkspaceNode) => {
    if (node.type !== "file") return;
    const relativePath = toWorkspaceRelativePath(node.path);
    if (!relativePath) {
      toast.error("Missing workspace file path.");
      return;
    }
    const nodeKey = getNodeKey(node.path);
    setDownloadingKeys((prev) => {
      const next = new Set(prev);
      next.add(nodeKey);
      return next;
    });
    try {
      const virtualPath = buildWorkspacePath(node.path);
      const response = await fetch(
        `/api/workspace?path=${encodeURIComponent(virtualPath)}`,
        { cache: "no-store" }
      );
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          data?.error || `Failed to download ${node.name || "file"}`
        );
      }
      const contentType = response.headers.get("content-type") || "";
      let blob: Blob;
      let fileName = node.name || relativePath.split("/").pop() || "download";
      if (contentType.includes("application/json")) {
        const data = await response.json().catch(() => ({}));
        if (typeof data?.error === "string") {
          throw new Error(data.error);
        }
        if (typeof data?.name === "string") {
          fileName = data.name;
        }
        if (typeof data?.content === "string") {
          const mimeType =
            typeof data?.mimeType === "string" ? data.mimeType : "text/plain";
          blob = new Blob([data.content], { type: mimeType });
        } else {
          blob = new Blob([JSON.stringify(data, null, 2)], {
            type: "application/json",
          });
          if (!fileName.endsWith(".json")) {
            fileName = `${fileName}.json`;
          }
        }
      } else {
        blob = await response.blob();
        const headerName = parseContentDispositionFilename(
          response.headers.get("content-disposition")
        );
        if (headerName) {
          fileName = headerName;
        }
      }
      const safeFileName =
        fileName.split("/").pop()?.split("\\").pop() || "download";
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = safeFileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      toast.success(`Downloaded ${safeFileName}`);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, "Failed to download file"));
    } finally {
      setDownloadingKeys((prev) => {
        const next = new Set(prev);
        next.delete(nodeKey);
        return next;
      });
    }
  }, []);

  const renderNode = useCallback(
    (node: WorkspaceNode, depth: number) => {
      const nodeKey = getNodeKey(node.path);
      const displayPath = buildWorkspaceDisplayPath(node.path);
      const isDirectory = node.type === "directory";
      const isExpanded = expanded.has(nodeKey);
      const indent = depth * 16 + 8;
      const isDownloading = downloadingKeys.has(nodeKey);

      const rowContent = (
        <>
          {isDirectory ? (
            isExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )
          ) : (
            <span className="h-4 w-4" />
          )}
          {isDirectory ? (
            <Folder className="h-4 w-4 text-muted-foreground" />
          ) : (
            <FileText className="h-4 w-4 text-muted-foreground" />
          )}
          <span
            className="min-w-0 flex-1 truncate text-sm text-foreground"
            title={displayPath}
          >
            {node.name}
          </span>
          {node.type === "file" && (
            <div className="flex items-center gap-2">
              {node.size != null && (
                <span className="text-xs text-muted-foreground">
                  {formatBytes(node.size)}
                </span>
              )}
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={(event) => {
                  event.stopPropagation();
                  handleDownload(node);
                }}
                disabled={isDownloading}
                aria-label={`Download ${node.name}`}
              >
                {isDownloading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
              </Button>
            </div>
          )}
        </>
      );

      return (
        <div key={nodeKey}>
          {isDirectory ? (
            <button
              type="button"
              onClick={() => toggleExpanded(nodeKey)}
              className="flex w-full items-center gap-2 rounded-md px-2 py-1 text-left hover:bg-accent/60"
              style={{ paddingLeft: indent }}
              aria-expanded={isExpanded}
            >
              {rowContent}
            </button>
          ) : (
            <div
              className="flex w-full items-center gap-2 rounded-md px-2 py-1 text-left"
              style={{ paddingLeft: indent }}
            >
              {rowContent}
            </div>
          )}
          {isDirectory &&
            isExpanded &&
            node.children &&
            node.children.map((child) => renderNode(child, depth + 1))}
        </div>
      );
    },
    [downloadingKeys, expanded, handleDownload, toggleExpanded]
  );

  const treeContent = (() => {
    if (isLoading) {
      return (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Loading workspace...
        </div>
      );
    }

    if (!tree) {
      return (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          Workspace data unavailable.
        </div>
      );
    }

    if (!tree.children || tree.children.length === 0) {
      return (
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          No files found in /workspace.
        </div>
      );
    }

    return renderNode(tree, 0);
  })();

  return (
    <Dialog
      open={open}
      onOpenChange={setOpen}
    >
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
        >
          Workspace
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] max-w-4xl overflow-hidden">
        <DialogHeader>
          <DialogTitle>Workspace files</DialogTitle>
          <DialogDescription>
            Upload files to /workspace and browse the directory tree.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Upload
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Drop files into /workspace or browse to upload.
                </p>
              </div>
              {isUploading && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Uploading...
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={openFilePicker}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              disabled={isUploading}
              className={cn(
                "mt-4 flex min-h-[160px] w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-6 text-center transition-colors",
                isDragging
                  ? "border-primary bg-primary/5"
                  : "border-border/60 bg-muted/30",
                isUploading
                  ? "cursor-not-allowed opacity-60"
                  : "hover:border-primary/60 hover:bg-primary/5"
              )}
            >
              <Upload className="h-6 w-6 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">
                Drop files here
              </span>
              <span className="text-xs text-muted-foreground">
                or click to browse
              </span>
            </button>
            <p className="mt-3 text-xs text-muted-foreground">
              Files are stored under /workspace for agent access.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="sr-only"
              onChange={(event) => handleUpload(event.target.files)}
            />
          </div>

          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Workspace tree
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {treeSummary}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={expandAll}
                  disabled={!tree?.children?.length}
                >
                  Expand all
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={collapseAll}
                  disabled={!tree?.children?.length}
                >
                  Collapse
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={fetchTree}
                  disabled={isLoading}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Refresh
                </Button>
              </div>
            </div>
            <ScrollArea className="mt-3 h-[360px] pr-2">
              {treeContent}
            </ScrollArea>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

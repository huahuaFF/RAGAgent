export type StoredFile = {
  name: string;
  path: string;
  size: number;
};

export type ImportStats = {
  total: number;
  loaded: number;
  skipped: number;
  failed: number;
};

export type PreviewResult = {
  rank: number;
  metadata: Record<string, unknown>;
  content_preview: string;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};
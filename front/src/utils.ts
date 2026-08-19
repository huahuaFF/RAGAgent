export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function metaText(metadata: Record<string, unknown>): string {
  const file = String(metadata.file_name ?? metadata.source ?? "unknown");
  const pageStart = metadata.page_start ? `p.${metadata.page_start}` : "page unknown";
  const section = String(metadata.section ?? "unknown");
  return `${file} · ${pageStart} · ${section}`;
}
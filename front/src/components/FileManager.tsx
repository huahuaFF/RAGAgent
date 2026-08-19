import { ChangeEvent, RefObject } from "react";
import { CheckCircle2, Database, FileText, Loader2, RefreshCw, Upload } from "lucide-react";
import { StoredFile } from "../types";
import { formatBytes } from "../utils";

type Props = {
  files: StoredFile[];
  selected: Set<string>;
  selectedCount: number;
  reindex: boolean;
  status: string;
  uploading: boolean;
  importing: boolean;
  inputRef: RefObject<HTMLInputElement | null>;
  onUpload: () => void;
  onImport: () => void;
  onRefresh: () => void;
  onToggleFile: (path: string) => void;
  onReindexChange: (value: boolean) => void;
};

export function FileManager({
  files,
  selected,
  selectedCount,
  reindex,
  status,
  uploading,
  importing,
  inputRef,
  onUpload,
  onImport,
  onRefresh,
  onToggleFile,
  onReindexChange,
}: Props) {
  return (
    <>
      <section className="tool-section">
        <div className="section-title"><Upload size={17} /> Upload</div>
        <input ref={inputRef} className="file-input" type="file" multiple accept=".pdf,.txt" />
        <button className="button primary" onClick={onUpload} disabled={uploading}>
          {uploading ? <Loader2 className="spin" size={16} /> : <Upload size={16} />}
          Upload files
        </button>
      </section>

      <section className="tool-section files-section">
        <div className="section-title row-between">
          <span><Database size={17} /> Database</span>
          <button className="icon-button" title="Refresh" onClick={onRefresh}><RefreshCw size={15} /></button>
        </div>
        <div className="file-list">
          {files.length === 0 ? (
            <div className="empty-state">No uploaded files.</div>
          ) : (
            files.map((file) => (
              <label className="file-row" key={file.path}>
                <input
                  type="checkbox"
                  checked={selected.has(file.path)}
                  onChange={() => onToggleFile(file.path)}
                />
                <FileText size={17} />
                <span>
                  <strong>{file.name}</strong>
                  <small>{formatBytes(file.size)}</small>
                </span>
              </label>
            ))
          )}
        </div>
        <label className="check-line">
          <input
            type="checkbox"
            checked={reindex}
            onChange={(event: ChangeEvent<HTMLInputElement>) => onReindexChange(event.target.checked)}
          />
          Reindex selected files
        </label>
        <button className="button primary" onClick={onImport} disabled={importing || selectedCount === 0}>
          {importing ? <Loader2 className="spin" size={16} /> : <CheckCircle2 size={16} />}
          Import selected
        </button>
        <div className="operation-status">{status}</div>
      </section>
    </>
  );
}
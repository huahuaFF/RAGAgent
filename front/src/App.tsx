import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Bot } from "lucide-react";
import { API_BASE, api } from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { FileManager } from "./components/FileManager";
import { RetrievalPreview } from "./components/RetrievalPreview";
import { ImportStats, Message, PreviewResult, StoredFile } from "./types";
import "./styles.css";

export default function App() {
  const [apiOnline, setApiOnline] = useState(false);
  const [files, setFiles] = useState<StoredFile[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [reindex, setReindex] = useState(false);
  const [status, setStatus] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const [lastQuery, setLastQuery] = useState("");
  const [answering, setAnswering] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [preview, setPreview] = useState<PreviewResult[]>([]);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const sessionIdRef = useRef(crypto.randomUUID());

  const selectedFiles = useMemo(
    () => files.filter((file) => selected.has(file.path)),
    [files, selected],
  );

  async function loadFiles() {
    const data = await api<{ files: StoredFile[] }>("/files");
    setFiles(data.files);
  }

  useEffect(() => {
    api<{ status: string }>("/health")
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
    loadFiles().catch((error) => setStatus(error.message));
  }, []);

  async function handleUpload() {
    const picked = inputRef.current?.files;
    if (!picked?.length) {
      setStatus("Select PDF or TXT files first.");
      return;
    }

    const body = new FormData();
    Array.from(picked).forEach((file) => body.append("files", file));

    setUploading(true);
    setStatus("Uploading files...");
    try {
      const data = await api<{ saved_files: string[] }>("/files/upload", { method: "POST", body });
      setSelected((current) => new Set([...current, ...data.saved_files]));
      if (inputRef.current) inputRef.current.value = "";
      await loadFiles();
      setStatus(`Uploaded ${data.saved_files.length} file(s).`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleImport() {
    if (!selected.size) {
      setStatus("Select files before importing.");
      return;
    }

    setImporting(true);
    setStatus("Updating vector database...");
    try {
      const stats = await api<ImportStats>("/knowledge/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_paths: Array.from(selected), reset: false, reindex }),
      });
      setStatus(
        `Selected ${stats.total}, loaded ${stats.loaded}, skipped ${stats.skipped}, failed ${stats.failed}.`,
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Import failed.");
    } finally {
      setImporting(false);
    }
  }

  function toggleFile(path: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  async function handleChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || answering) return;

    const userMessage: Message = { id: crypto.randomUUID(), role: "user", content: trimmed };
    const pendingId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      userMessage,
      { id: pendingId, role: "assistant", content: "Thinking..." },
    ]);
    setQuery("");
    setLastQuery(trimmed);
    setAnswering(true);

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, session_id: sessionIdRef.current }),
      });
      if (!response.ok || !response.body) {
        throw new Error(`${response.status} ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let answer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        answer += decoder.decode(value, { stream: true });
        setMessages((current) =>
          current.map((message) =>
            message.id === pendingId ? { ...message, content: answer || "Thinking..." } : message,
          ),
        );
      }
      answer += decoder.decode();
      setMessages((current) =>
        current.map((message) =>
          message.id === pendingId ? { ...message, content: answer || "No response." } : message,
        ),
      );
    } catch (error) {
      setMessages((current) =>
        current.map((message) =>
          message.id === pendingId
            ? { ...message, content: error instanceof Error ? error.message : "Request failed." }
            : message,
        ),
      );
    } finally {
      setAnswering(false);
    }
  }

  async function handlePreview() {
    const previewQuery = lastQuery || query.trim();
    if (!previewQuery) return;

    setPreviewing(true);
    try {
      const data = await api<{ results: PreviewResult[] }>(
        `/retrieval/preview?query=${encodeURIComponent(previewQuery)}&limit=8`,
      );
      setPreview(data.results);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Preview failed.");
    } finally {
      setPreviewing(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="side-pane">
        <header className="brand-row">
          <div className="brand-icon"><Bot size={22} /></div>
          <div>
            <h1>RAGAgent</h1>
            <span className={apiOnline ? "status-dot online" : "status-dot"}>
              {apiOnline ? "API online" : "API offline"}
            </span>
          </div>
        </header>

        <FileManager
          files={files}
          selected={selected}
          selectedCount={selectedFiles.length}
          reindex={reindex}
          status={status}
          uploading={uploading}
          importing={importing}
          inputRef={inputRef}
          onUpload={handleUpload}
          onImport={handleImport}
          onRefresh={() => loadFiles().catch((error) => setStatus(error.message))}
          onToggleFile={toggleFile}
          onReindexChange={setReindex}
        />
      </aside>

      <main className="work-area">
        <ChatPanel
          messages={messages}
          query={query}
          answering={answering}
          selectedCount={selectedFiles.length}
          uploadedCount={files.length}
          onQueryChange={setQuery}
          onSubmit={handleChat}
          onClear={() => setMessages([])}
        />
        <RetrievalPreview
          preview={preview}
          previewing={previewing}
          canPreview={Boolean(lastQuery || query.trim())}
          onPreview={handlePreview}
        />
      </main>
    </div>
  );
}
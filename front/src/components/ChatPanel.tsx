import { FormEvent } from "react";
import { Loader2, MessageSquare, Send } from "lucide-react";
import { Message } from "../types";

type Props = {
  messages: Message[];
  query: string;
  answering: boolean;
  selectedCount: number;
  uploadedCount: number;
  onQueryChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onClear: () => void;
};

export function ChatPanel({
  messages,
  query,
  answering,
  selectedCount,
  uploadedCount,
  onQueryChange,
  onSubmit,
  onClear,
}: Props) {
  return (
    <section className="chat-area">
      <div className="panel-header">
        <div>
          <h2>Paper QA</h2>
          <p>{selectedCount} selected · {uploadedCount} uploaded</p>
        </div>
        <button className="button secondary" onClick={onClear}>Clear</button>
      </div>
      <div className="messages">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <MessageSquare size={28} />
            <span>Ask a question after importing papers.</span>
          </div>
        ) : (
          messages.map((message) => (
            <div className={`message ${message.role}`} key={message.id}>{message.content}</div>
          ))
        )}
      </div>
      <form className="composer" onSubmit={onSubmit}>
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Ask about imported papers..."
        />
        <button className="button primary" type="submit" disabled={answering || !query.trim()}>
          {answering ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
          Send
        </button>
      </form>
    </section>
  );
}
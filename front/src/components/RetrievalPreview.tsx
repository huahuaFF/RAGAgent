import { Loader2, Search } from "lucide-react";
import { PreviewResult } from "../types";
import { metaText } from "../utils";

type Props = {
  preview: PreviewResult[];
  previewing: boolean;
  canPreview: boolean;
  onPreview: () => void;
};

export function RetrievalPreview({ preview, previewing, canPreview, onPreview }: Props) {
  return (
    <section className="preview-area">
      <div className="panel-header compact">
        <div>
          <h2>Retrieval</h2>
          <p>Top chunks for the latest query</p>
        </div>
        <button className="button secondary" onClick={onPreview} disabled={previewing || !canPreview}>
          {previewing ? <Loader2 className="spin" size={16} /> : <Search size={16} />}
          Preview
        </button>
      </div>
      <div className="preview-list">
        {preview.length === 0 ? (
          <div className="empty-state">No retrieval preview.</div>
        ) : (
          preview.map((item) => (
            <article className="preview-item" key={`${item.rank}-${metaText(item.metadata)}`}>
              <div className="preview-rank">#{item.rank}</div>
              <div className="preview-meta">{metaText(item.metadata)}</div>
              <p className="chunk-scroll">{item.content_preview}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
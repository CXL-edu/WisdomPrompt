import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

export default function Docs() {
  const [md, setMd] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/docs/index.md")
      .then((r) => (r.ok ? r.text() : ""))
      .then(setMd)
      .catch(() => setMd(""))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-container pb-20 pt-14">
      <div className="card p-8 sm:p-10 fade-up">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Documentation</p>
            <h1 className="font-display text-3xl font-semibold text-slate-900">产品文档</h1>
          </div>
          <span className="badge">Markdown</span>
        </div>
        <div className="mt-6">
          {loading && <p className="text-slate-500">加载中…</p>}
          {!loading && md && (
            <article className="markdown">
              <ReactMarkdown>{md}</ReactMarkdown>
            </article>
          )}
          {!loading && !md && (
            <p className="text-slate-600">
              暂无文档内容。可将 Markdown 放入 <code>public/docs/</code>。
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

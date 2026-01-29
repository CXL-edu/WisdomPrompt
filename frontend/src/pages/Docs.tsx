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
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">文档</h1>
      {loading && <p className="text-slate-500">加载中…</p>}
      {!loading && md && (
        <article className="prose prose-slate max-w-none">
          <ReactMarkdown>{md}</ReactMarkdown>
        </article>
      )}
      {!loading && !md && (
        <p className="text-slate-600">暂无文档内容。可将 Markdown 放入 <code>public/docs/</code>。</p>
      )}
    </div>
  );
}

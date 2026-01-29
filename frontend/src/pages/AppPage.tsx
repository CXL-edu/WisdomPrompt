import { useCallback, useState } from "react";
import ReactMarkdown from "react-markdown";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const WORKFLOW_STREAM = `${API_BASE}/api/v1/workflow/stream`;

type SubTaskState = {
  name: string;
  status: "pending" | "loading" | "done" | "error";
  hits?: { content: string; url?: string; source?: string }[];
  summary?: string;
  error?: string;
};

export default function AppPage() {
  const [query, setQuery] = useState("");
  const [running, setRunning] = useState(false);
  const [subTasks, setSubTasks] = useState<string[]>([]);
  const [subTaskStates, setSubTaskStates] = useState<SubTaskState[]>([]);
  const [finalAnswer, setFinalAnswer] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<number, boolean>>({});

  const toggleCollapsed = useCallback((i: number) => {
    setCollapsed((c) => ({ ...c, [i]: !c[i] }));
  }, []);

  const runWorkflow = useCallback(async () => {
    if (!query.trim()) return;
    setError(null);
    setRunning(true);
    setSubTasks([]);
    setSubTaskStates([]);
    setFinalAnswer("");
    setStreaming(false);

    try {
      const res = await fetch(WORKFLOW_STREAM, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim(), from_step: 1 }),
      });
      if (!res.ok || !res.body) throw new Error(res.statusText || "Stream failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";
      let currentData = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("event: ")) currentEvent = line.slice(7).trim();
          else if (line.startsWith("data: ")) currentData = line.slice(6);
          else if (line === "" && currentEvent && currentData) {
            try {
              const data = JSON.parse(currentData);
              if (currentEvent === "step1_sub_tasks") {
                const tasks = (data.sub_tasks || []) as string[];
                setSubTasks(tasks);
                setSubTaskStates(tasks.map((name) => ({ name, status: "pending" as const })));
              } else if (currentEvent === "step2_retrieval_start") {
                const i = data.index as number;
                setSubTaskStates((s) =>
                  s.map((t, j) => (j === i ? { ...t, status: "loading" as const } : t))
                );
              } else if (currentEvent === "step2_retrieval_done") {
                const i = data.index as number;
                const hits = (data.hits || []).map((h: { content?: string; url?: string; source?: string }) => ({
                  content: h.content || "",
                  url: h.url,
                  source: h.source,
                }));
                setSubTaskStates((s) =>
                  s.map((t, j) => (j === i ? { ...t, status: "done" as const, hits } : t))
                );
              } else if (currentEvent === "step3_summary_done") {
                const i = data.index as number;
                setSubTaskStates((s) =>
                  s.map((t, j) => (j === i ? { ...t, summary: data.summary as string } : t))
                );
              } else if (currentEvent === "step4_chunk") {
                setStreaming(true);
                setFinalAnswer((prev) => prev + (data.text || ""));
              } else if (currentEvent === "step4_done") {
                setStreaming(false);
              } else if (currentEvent === "error") {
                setError((data.message as string) || "Unknown error");
              }
            } catch (_) {}
            currentEvent = "";
            currentData = "";
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setRunning(false);
    }
  }, [query]);

  const copyAsMarkdown = useCallback(() => {
    if (!finalAnswer) return;
    navigator.clipboard.writeText(finalAnswer);
  }, [finalAnswer]);

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-6">产品页</h1>
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>
      )}
      <div className="flex gap-2 mb-8">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && runWorkflow()}
          placeholder="输入你的问题..."
          className="flex-1 border border-slate-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-slate-400"
          disabled={running}
        />
        <button
          type="button"
          onClick={runWorkflow}
          disabled={running}
          className="px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 disabled:opacity-50"
        >
          {running ? "运行中…" : "提交"}
        </button>
      </div>

      {subTasks.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">子任务</h2>
          <ul className="list-disc list-inside text-slate-600 space-y-1">
            {subTasks.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </section>
      )}

      {subTaskStates.length > 0 && (
        <section className="mb-8 space-y-3">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">检索与整理</h2>
          {subTaskStates.map((st, i) => (
            <div
              key={i}
              className="border border-slate-200 rounded-lg bg-white overflow-hidden"
            >
              <button
                type="button"
                onClick={() => toggleCollapsed(i)}
                className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-slate-50"
              >
                <span className="font-medium text-slate-800">{st.name}</span>
                <span className="text-slate-500 text-sm">
                  {st.status === "pending" && "待处理"}
                  {st.status === "loading" && "检索中…"}
                  {st.status === "done" && (collapsed[i] ? "展开" : "收起")}
                </span>
              </button>
              {!collapsed[i] && (
                <div className="px-4 pb-4 border-t border-slate-100">
                  {st.status === "loading" && (
                    <p className="text-slate-500 py-2">正在检索与拉取正文…</p>
                  )}
                  {st.hits && st.hits.length > 0 && (
                    <div className="mt-2 space-y-2">
                      {st.hits.map((h, j) => (
                        <div key={j} className="text-sm text-slate-600 bg-slate-50 p-2 rounded">
                          {h.url && (
                            <a
                              href={h.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:underline block mb-1"
                            >
                              {h.url}
                            </a>
                          )}
                          <p className="line-clamp-3">{h.content}</p>
                        </div>
                      ))}
                    </div>
                  )}
                  {st.summary && (
                    <div className="mt-3 p-3 bg-slate-50 rounded text-slate-700">
                      <p className="text-sm font-medium text-slate-600 mb-1">整理结果</p>
                      <p className="text-sm whitespace-pre-wrap">{st.summary}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {(finalAnswer || streaming) && (
        <section className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xl font-semibold text-slate-800">最终答案</h2>
            <button
              type="button"
              onClick={copyAsMarkdown}
              className="text-sm px-3 py-1 border border-slate-300 rounded hover:bg-slate-100"
            >
              一键复制为 Markdown
            </button>
          </div>
          <div className="border border-slate-200 rounded-lg bg-white p-4 min-h-[120px] prose prose-slate max-w-none">
            <ReactMarkdown>{finalAnswer || (streaming ? "…" : "")}</ReactMarkdown>
          </div>
        </section>
      )}
    </div>
  );
}

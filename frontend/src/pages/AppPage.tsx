import { useCallback, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const WORKFLOW_DECOMPOSE = `${API_BASE}/api/v1/workflow/decompose`;
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
  const [decomposeLoading, setDecomposeLoading] = useState(false);
  const [subTasks, setSubTasks] = useState<string[]>([]);
  const [subTaskStates, setSubTaskStates] = useState<SubTaskState[]>([]);
  const [finalAnswer, setFinalAnswer] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<number, boolean>>({});
  const streamAbortRef = useRef<AbortController | null>(null);

  const toggleCollapsed = useCallback((i: number) => {
    setCollapsed((c) => ({ ...c, [i]: !c[i] }));
  }, []);

  const updateSubTask = useCallback((index: number, value: string) => {
    setSubTasks((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }, []);

  const removeSubTask = useCallback((index: number) => {
    setSubTasks((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const addSubTask = useCallback(() => {
    setSubTasks((prev) => [...prev, ""]);
  }, []);

  const runDecomposeOnly = useCallback(async () => {
    if (!query.trim()) return;
    if (streamAbortRef.current) {
      streamAbortRef.current.abort();
      streamAbortRef.current = null;
    }
    setError(null);
    setRunning(false);
    setSubTaskStates([]);
    setFinalAnswer("");
    setDecomposeLoading(true);
    setSubTasks([]);
    try {
      const res = await fetch(WORKFLOW_DECOMPOSE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      });
      if (!res.ok) throw new Error(res.statusText || "Decompose failed");
      const data = await res.json();
      const tasks = (data.sub_tasks || []) as string[];
      setSubTasks(tasks.length ? tasks : [query.trim()]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Decompose failed");
    } finally {
      setDecomposeLoading(false);
    }
  }, [query]);

  const runFromStep2 = useCallback(async () => {
    const tasks = subTasks.filter((t) => t.trim());
    if (!query.trim() || tasks.length === 0) return;
    if (streamAbortRef.current) {
      streamAbortRef.current.abort();
      streamAbortRef.current = null;
    }
    const ac = new AbortController();
    streamAbortRef.current = ac;
    const signal = ac.signal;
    setError(null);
    setRunning(true);
    setSubTaskStates(tasks.map((name) => ({ name, status: "pending" as const })));
    setFinalAnswer("");
    setStreaming(false);

    try {
      const res = await fetch(WORKFLOW_STREAM, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          from_step: 2,
          cached: { sub_tasks: tasks },
        }),
        signal,
      });
      if (!res.ok || !res.body) throw new Error(res.statusText || "Stream failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";
      let currentData = "";

      while (true) {
        if (signal.aborted) break;
        const { done, value } = await reader.read();
        if (done) break;
        if (signal.aborted) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("event: ")) currentEvent = line.slice(7).trim();
          else if (line.startsWith("data: ")) currentData = line.slice(6);
          else if (line === "" && currentEvent && currentData) {
            if (signal.aborted) break;
            try {
              const data = JSON.parse(currentData);
              if (currentEvent === "step2_retrieval_start") {
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
      if (e instanceof Error && e.name === "AbortError") {
        if (streamAbortRef.current === ac) streamAbortRef.current = null;
        return;
      }
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      if (streamAbortRef.current === ac) streamAbortRef.current = null;
      setRunning(false);
    }
  }, [query, subTasks]);

  const copyAsMarkdown = useCallback(() => {
    if (!finalAnswer) return;
    navigator.clipboard.writeText(finalAnswer);
  }, [finalAnswer]);

  const canConfirm = subTasks.some((t) => t.trim().length > 0);
  const hasRunOnce = !running && (finalAnswer.length > 0 || subTaskStates.some((s) => s.status === "done"));

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
          onKeyDown={(e) => e.key === "Enter" && runDecomposeOnly()}
          placeholder="输入你的问题..."
          className="flex-1 border border-slate-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-slate-400"
          disabled={decomposeLoading}
        />
        <button
          type="button"
          onClick={runDecomposeOnly}
          disabled={decomposeLoading}
          className="px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 disabled:opacity-50"
        >
          {decomposeLoading ? "分解中…" : subTasks.length > 0 ? "重新分解" : "分解子任务"}
        </button>
      </div>

      {subTasks.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">子任务（可编辑，确认后执行检索）</h2>
          <ul className="space-y-2">
            {subTasks.map((t, i) => (
              <li key={i} className="flex gap-2 items-center">
                <input
                  type="text"
                  value={t}
                  onChange={(e) => updateSubTask(i, e.target.value)}
                  placeholder={`子任务 ${i + 1}`}
                  className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  disabled={running}
                />
                <button
                  type="button"
                  onClick={() => removeSubTask(i)}
                  disabled={running || subTasks.length <= 1}
                  className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded disabled:opacity-50"
                  title="删除"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={addSubTask}
              disabled={running}
              className="text-sm px-3 py-1.5 border border-slate-300 rounded-lg hover:bg-slate-100 disabled:opacity-50"
            >
              + 添加子任务
            </button>
            <button
              type="button"
              onClick={runFromStep2}
              disabled={running || !canConfirm}
              className="px-4 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 disabled:opacity-50"
            >
              {running ? "运行中…" : hasRunOnce ? "重新执行" : "确认并执行"}
            </button>
          </div>
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

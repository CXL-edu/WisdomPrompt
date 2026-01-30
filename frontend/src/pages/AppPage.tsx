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
    <div className="page-container pb-20 pt-14">
      <header className="space-y-4 fade-up">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Product Workspace</p>
        <h1 className="font-display text-3xl font-semibold text-slate-900 sm:text-4xl">问题拆解与答案生成</h1>
        <p className="max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
          输入问题后，系统会自动拆成子任务，分别检索与整理，最终输出结构化答案。你可以在执行前调整子任务。
        </p>
      </header>

      <div className="mt-8 grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="card p-6 sm:p-8 fade-up">
          {error && (
            <div
              role="alert"
              className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
            >
              {error}
            </div>
          )}
          <div className="space-y-4">
            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
              Step 1 · 输入问题
            </label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runDecomposeOnly()}
                placeholder="输入你的问题..."
                className="input-field flex-1"
                disabled={decomposeLoading}
                aria-label="输入问题"
              />
              <button
                type="button"
                onClick={runDecomposeOnly}
                disabled={decomposeLoading}
                className="btn-primary"
              >
                {decomposeLoading ? "分解中…" : subTasks.length > 0 ? "重新分解" : "分解子任务"}
              </button>
            </div>
          </div>

          {subTasks.length > 0 && (
            <section className="mt-8">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                    Step 2 · 子任务编辑
                  </p>
                  <h2 className="section-title">确认检索范围</h2>
                </div>
                <span className="badge">{subTasks.length} 个子任务</span>
              </div>
              <ul className="mt-4 space-y-3">
                {subTasks.map((t, i) => (
                  <li key={i} className="flex flex-col gap-2 sm:flex-row sm:items-center">
                    <input
                      type="text"
                      value={t}
                      onChange={(e) => updateSubTask(i, e.target.value)}
                      placeholder={`子任务 ${i + 1}`}
                      className="input-field flex-1"
                      disabled={running}
                    />
                    <button
                      type="button"
                      onClick={() => removeSubTask(i)}
                      disabled={running || subTasks.length <= 1}
                      className="btn-secondary px-3 py-2 text-slate-500 hover:text-red-600"
                      title="删除"
                    >
                      删除
                    </button>
                  </li>
                ))}
              </ul>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={addSubTask}
                  disabled={running}
                  className="btn-secondary"
                >
                  添加子任务
                </button>
                <button
                  type="button"
                  onClick={runFromStep2}
                  disabled={running || !canConfirm}
                  className="btn-primary"
                >
                  {running ? "运行中…" : hasRunOnce ? "重新执行" : "确认并执行"}
                </button>
              </div>
            </section>
          )}
        </section>

        <aside className="card-tight p-6 sm:p-7 fade-up">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">实时进度</p>
          <h3 className="mt-2 font-display text-2xl font-semibold text-slate-900">当前状态</h3>
          <div className="mt-4 space-y-3 text-sm text-slate-600">
            <div className="flex items-center justify-between">
              <span>分解任务</span>
              <span className="text-slate-800">{decomposeLoading ? "进行中" : "就绪"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>检索执行</span>
              <span className="text-slate-800">{running ? "执行中" : subTaskStates.length ? "完成" : "等待"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>答案生成</span>
              <span className="text-slate-800">{streaming ? "输出中" : finalAnswer ? "完成" : "等待"}</span>
            </div>
          </div>
          <div className="mt-6 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-500">
            提示：可先分解任务，再手动调整，以获得更准确的检索结果。
          </div>
        </aside>
      </div>

      {subTaskStates.length > 0 && (
        <section className="mt-8 space-y-4 fade-up">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Step 3 · 检索与整理
              </p>
              <h2 className="section-title">检索结果与摘要</h2>
            </div>
            <span className="badge">同步更新</span>
          </div>
          {subTaskStates.map((st, i) => (
            <div key={i} className="card-tight overflow-hidden">
              <button
                type="button"
                onClick={() => toggleCollapsed(i)}
                aria-expanded={!collapsed[i]}
                className="flex w-full items-center justify-between px-5 py-4 text-left transition hover:bg-slate-50"
              >
                <span className="font-medium text-slate-900">{st.name}</span>
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                  {st.status === "pending" && "待处理"}
                  {st.status === "loading" && "检索中"}
                  {st.status === "done" && (collapsed[i] ? "展开" : "收起")}
                </span>
              </button>
              {!collapsed[i] && (
                <div className="border-t border-slate-100 px-5 pb-5">
                  {st.status === "loading" && (
                    <p className="py-2 text-sm text-slate-500">正在检索与拉取正文…</p>
                  )}
                  {st.hits && st.hits.length > 0 && (
                    <div className="mt-2 space-y-3">
                      {st.hits.map((h, j) => (
                        <div key={j} className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
                          {h.url && (
                            <a
                              href={h.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="mb-1 block text-blue-600 underline-offset-4 hover:underline"
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
                    <div className="mt-4 rounded-xl bg-slate-50 p-4 text-slate-700">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">整理结果</p>
                      <p className="mt-2 text-sm whitespace-pre-wrap">{st.summary}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {(finalAnswer || streaming) && (
        <section className="mt-8 fade-up">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Step 4 · 最终答案
              </p>
              <h2 className="section-title">可直接复制的结果</h2>
            </div>
            <button type="button" onClick={copyAsMarkdown} className="btn-secondary">
              一键复制为 Markdown
            </button>
          </div>
          <div className="card mt-4 min-h-[160px] p-5 markdown">
            <ReactMarkdown>{finalAnswer || (streaming ? "…" : "")}</ReactMarkdown>
          </div>
        </section>
      )}
    </div>
  );
}

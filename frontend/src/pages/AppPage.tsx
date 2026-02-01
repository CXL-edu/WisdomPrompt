import { useCallback, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const WORKFLOW_DECOMPOSE = `${API_BASE}/api/v1/workflow/decompose`;
const WORKFLOW_STREAM = `${API_BASE}/api/v1/workflow/stream`;

const createTaskId = () => Math.random().toString(36).slice(2, 10);

type SubTaskInput = {
  id: string;
  value: string;
};

type SubTaskState = {
  id: string;
  name: string;
  status: "pending" | "loading" | "done" | "error";
  hits?: { content: string; url?: string; source?: string }[];
  summary?: string;
  error?: string;
};

export default function AppPage() {
  const [query, setQuery] = useState("");
  const [decomposeLoading, setDecomposeLoading] = useState(false);
  const [subTasks, setSubTasks] = useState<SubTaskInput[]>([]);
  const [subTaskStates, setSubTaskStates] = useState<SubTaskState[]>([]);
  const [finalAnswer, setFinalAnswer] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<number, boolean>>({});
  const streamAbortRef = useRef<AbortController | null>(null);
  const hasDecomposed = decomposeLoading || subTasks.length > 0;
  const hasRun = running || subTaskStates.length > 0 || streaming || finalAnswer.length > 0;
  const retrievalActive = subTaskStates.some((s) => s.status === "loading");
  const retrievalDone =
    subTaskStates.length > 0 && subTaskStates.every((s) => s.status === "done" || s.status === "error");
  const summaryDone =
    subTaskStates.length > 0 && subTaskStates.every((s) => Boolean(s.summary) || s.status === "error");
  const hasTaskError = subTaskStates.some((s) => s.status === "error");

  const toggleCollapsed = useCallback((i: number) => {
    setCollapsed((c) => ({ ...c, [i]: !c[i] }));
  }, []);

  const isCollapsed = useCallback((i: number) => collapsed[i] ?? false, [collapsed]);

  const setAllCollapsed = useCallback(
    (value: boolean) => {
      setCollapsed(() => Object.fromEntries(subTaskStates.map((_, i) => [i, value])));
    },
    [subTaskStates]
  );

  const updateSubTask = useCallback((index: number, value: string) => {
    setSubTasks((prev) => {
      const next = [...prev];
      const current = next[index];
      if (!current) return next;
      next[index] = { ...current, value };
      return next;
    });
  }, []);

  const removeSubTask = useCallback((index: number) => {
    setSubTasks((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const addSubTask = useCallback(() => {
    setSubTasks((prev) => [...prev, { id: createTaskId(), value: "" }]);
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
    setCollapsed({});
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
      const nextTasks = tasks.length ? tasks : [query.trim()];
      setSubTasks(nextTasks.map((task) => ({ id: createTaskId(), value: task })));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Decompose failed");
    } finally {
      setDecomposeLoading(false);
    }
  }, [query]);

  const runFromStep2 = useCallback(async () => {
    const activeTasks = subTasks
      .map((task) => ({ ...task, value: task.value.trim() }))
      .filter((task) => task.value);
    if (!query.trim() || activeTasks.length === 0) return;
    if (streamAbortRef.current) {
      streamAbortRef.current.abort();
      streamAbortRef.current = null;
    }
    const ac = new AbortController();
    streamAbortRef.current = ac;
    const signal = ac.signal;
    setError(null);
    setRunning(true);
    setSubTaskStates(activeTasks.map((task) => ({ id: task.id, name: task.value, status: "pending" as const })));
    setCollapsed(Object.fromEntries(activeTasks.map((_, i) => [i, true])));
    setFinalAnswer("");
    setStreaming(false);

    try {
      const res = await fetch(WORKFLOW_STREAM, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: query.trim(),
            from_step: 2,
            cached: { sub_tasks: activeTasks.map((task) => task.value) },
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
                setCollapsed(() => {
                  const next: Record<number, boolean> = {};
                  for (let j = 0; j < activeTasks.length; j += 1) {
                    next[j] = j !== i;
                  }
                  return next;
                });
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
                const message = (data.message as string) || "Unknown error";
                setError(message);
                setSubTaskStates((s) =>
                  s.map((t) =>
                    t.status === "loading" || t.status === "pending"
                      ? { ...t, status: "error" as const, error: message }
                      : t
                  )
                );
              }
            } catch (err) {
              void err;
            }
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

  const canConfirm = subTasks.some((t) => t.value.trim().length > 0);
  const hasRunOnce = !running && (finalAnswer.length > 0 || subTaskStates.some((s) => s.status === "done"));
  const doneCount = subTaskStates.filter((s) => s.status === "done").length;
  const allCollapsed = subTaskStates.length > 0 && subTaskStates.every((_, i) => isCollapsed(i));
  const allExpanded = subTaskStates.length > 0 && subTaskStates.every((_, i) => !isCollapsed(i));
  const showProgress = hasDecomposed || hasRun || Boolean(error);
  const canCopy = finalAnswer.length > 0 && !streaming;

  const getTaskPreview = (task: SubTaskState) => {
    if (task.error) return `错误：${task.error}`;
    if (task.summary) {
      const firstLine = task.summary.split("\n").find((line) => line.trim());
      return (firstLine || "已整理").slice(0, 80);
    }
    if (task.hits && task.hits.length > 0) return `${task.hits.length} 条来源`;
    if (task.status === "loading") return "正在检索中…";
    return "待处理";
  };

  const progressSteps = [
    {
      key: "decompose",
      label: "分解任务",
      state: decomposeLoading ? "active" : subTasks.length > 0 ? "done" : "idle",
      text: decomposeLoading ? "进行中" : subTasks.length > 0 ? "完成" : "等待",
    },
    {
      key: "retrieval",
      label: "检索执行",
      state: hasTaskError ? "error" : retrievalActive ? "active" : retrievalDone ? "done" : hasRun ? "idle" : "idle",
      text: hasTaskError ? "失败" : retrievalActive ? "检索中" : retrievalDone ? "完成" : "等待",
    },
    {
      key: "summary",
      label: "摘要整理",
      state: hasTaskError ? "error" : summaryDone ? "done" : retrievalDone ? "active" : "idle",
      text: hasTaskError ? "中断" : summaryDone ? "完成" : retrievalDone ? "整理中" : "等待",
    },
    {
      key: "answer",
      label: "答案生成",
      state: streaming ? "active" : finalAnswer ? "done" : hasRun ? "idle" : "idle",
      text: streaming ? "输出中" : finalAnswer ? "完成" : "等待",
    },
  ];

  return (
    <div className="page-container pb-20 pt-14">
      <header className="space-y-4 fade-up">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Product Workspace</p>
        <h1 className="font-display text-3xl font-semibold text-slate-900 sm:text-4xl">问题拆解与答案生成</h1>
        <p className="max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
          输入问题后，系统会自动拆成子任务，分别检索与整理，最终输出结构化答案。你可以在执行前调整子任务。
        </p>
      </header>

      <div className={`mt-8 grid gap-6 ${showProgress ? "lg:grid-cols-[2fr_1fr]" : ""}`}>
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
            <label
              htmlFor="query-input"
              className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500"
            >
              Step 1 · 输入问题
            </label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                id="query-input"
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
            {!hasDecomposed && (
              <p className="text-xs text-slate-500">完成分解后将显示检索进度与结果。</p>
            )}
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
                  <li key={t.id} className="flex flex-col gap-2 sm:flex-row sm:items-center">
                    <input
                      type="text"
                      value={t.value}
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

        {showProgress && (
          <aside
            className="card-tight p-6 sm:p-7 fade-up"
            aria-live="polite"
            aria-busy={decomposeLoading || running || streaming}
          >
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">实时进度</p>
              {(decomposeLoading || running || streaming) && (
                <span className="status-badge">
                  <span className="pulse-dot" aria-hidden="true" />
                  {streaming ? "输出中" : running ? "运行中" : "分解中"}
                </span>
              )}
            </div>
            <h3 className="mt-2 font-display text-2xl font-semibold text-slate-900">当前状态</h3>
            <div className="mt-4 space-y-3 text-sm text-slate-600">
              {progressSteps.map((step) => (
                <div key={step.key} className="progress-row">
                  <span>{step.label}</span>
                  <span className="progress-state">
                    <span className={`status-dot status-dot--${step.state}`} aria-hidden="true" />
                    <span className="text-slate-800">{step.text}</span>
                  </span>
                </div>
              ))}
            </div>
            {!hasRun && (
              <div className="mt-6 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-500">
                提示：先分解任务，再确认子任务，即可开始检索。
              </div>
            )}
            {hasRun && (
              <div className="mt-6 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-500">
                点击子任务可展开详情，查看检索来源与整理结果。
              </div>
            )}
          </aside>
        )}
      </div>

      {subTaskStates.length > 0 && (
        <section className="mt-8 space-y-4 fade-up">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Step 3 · 检索与整理
              </p>
              <h2 className="section-title">检索结果与摘要</h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="badge">
                {doneCount}/{subTaskStates.length} 已完成
              </span>
              <button
                type="button"
                onClick={() => setAllCollapsed(false)}
                disabled={allExpanded}
                className="btn-secondary px-3 py-1 text-xs"
              >
                展开全部
              </button>
              <button
                type="button"
                onClick={() => setAllCollapsed(true)}
                disabled={allCollapsed}
                className="btn-secondary px-3 py-1 text-xs"
              >
                收起全部
              </button>
            </div>
          </div>
          {subTaskStates.map((st, i) => {
            const collapsedState = isCollapsed(i);
            const statusLabel =
              st.status === "loading"
                ? "检索中"
                : st.status === "error"
                ? "失败"
                : st.status === "done"
                ? collapsedState
                  ? "展开"
                  : "收起"
                : "待处理";
            const statusDot =
              st.status === "loading"
                ? "active"
                : st.status === "error"
                ? "error"
                : st.status === "done"
                ? "done"
                : "idle";

            return (
              <div key={st.id} className="card-tight overflow-hidden">
                <button
                  type="button"
                  onClick={() => toggleCollapsed(i)}
                  aria-expanded={!collapsedState}
                  aria-controls={`subtask-panel-${st.id}`}
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition hover:bg-slate-50"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <span className={`status-dot status-dot--${statusDot}`} aria-hidden="true" />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-slate-900">{st.name}</span>
                        {st.hits && st.hits.length > 0 && (
                          <span className="badge">{st.hits.length} 源</span>
                        )}
                      </div>
                      {collapsedState && (
                        <p className="mt-1 line-clamp-1 text-xs text-slate-500">{getTaskPreview(st)}</p>
                      )}
                    </div>
                  </div>
                  <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                    {statusLabel}
                  </span>
                </button>
                <div
                  id={`subtask-panel-${st.id}`}
                  aria-hidden={collapsedState}
                  className={`collapse-panel ${collapsedState ? "collapse-panel--closed" : "collapse-panel--open"}`}
                >
                  <div className="border-t border-slate-100 px-5 pb-5">
                    {st.status === "loading" && (
                      <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">
                        <span className="status-dot status-dot--active" aria-hidden="true" />
                        正在检索与拉取正文…
                      </div>
                    )}
                    {st.status === "error" && st.error && (
                      <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                        {st.error}
                      </div>
                    )}
                    {st.summary && (
                      <div className="mt-4 rounded-xl bg-slate-50 p-4 text-slate-700">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">整理结果</p>
                        <p className="mt-2 text-sm whitespace-pre-wrap">{st.summary}</p>
                      </div>
                    )}
                    {st.hits && st.hits.length > 0 && (
                      <div className="mt-4 space-y-3">
                        {st.hits.map((h) => (
                          <div
                            key={`${h.url || h.source || "hit"}-${h.content.slice(0, 24)}`}
                            className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600"
                          >
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
                  </div>
                </div>
              </div>
            );
          })}
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
            <div className="flex items-center gap-2">
              {streaming && (
                <span className="status-badge">
                  <span className="pulse-dot" aria-hidden="true" />
                  输出中
                </span>
              )}
              <button type="button" onClick={copyAsMarkdown} disabled={!canCopy} className="btn-secondary">
                {canCopy ? "一键复制为 Markdown" : "生成中…"}
              </button>
            </div>
          </div>
          <div
            className="card mt-4 min-h-[160px] p-5 markdown"
            aria-live="polite"
            aria-busy={streaming}
          >
            {!finalAnswer && streaming && (
              <div className="space-y-3">
                <div className="skeleton h-4 w-2/3" />
                <div className="skeleton h-4 w-5/6" />
                <div className="skeleton h-4 w-1/2" />
              </div>
            )}
            <ReactMarkdown>{finalAnswer || (streaming ? "…" : "")}</ReactMarkdown>
          </div>
        </section>
      )}
    </div>
  );
}

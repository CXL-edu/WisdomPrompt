import { useEffect, useMemo, useState } from 'react'
import { confirmSubtasks, createRun, eventsUrl, getRun, rerunFromStep, type RunSnapshot, type Subtask } from './api'

type EventMsg = { id: number; event: string; data: any }

function nextOrder(subtasks: Subtask[]): number {
  return subtasks.length ? Math.max(...subtasks.map((s) => s.order)) + 1 : 0
}

export default function App() {
  const [query, setQuery] = useState('')
  const [run, setRun] = useState<RunSnapshot | null>(null)
  const [events, setEvents] = useState<EventMsg[]>([])
  const [error, setError] = useState<string | null>(null)

  const canConfirm = run?.status === 'waiting_confirm'
  const canStep2 = !!run && run.status !== 'waiting_confirm' && run.current_step >= 2
  const canStep3 = !!run && run.current_step >= 3
  const canStep4 = !!run && run.current_step >= 4

  useEffect(() => {
    if (!run?.run_id) return
    const es = new EventSource(eventsUrl(run.run_id))
    es.onmessage = () => {
      // We only use named events; ignore default.
    }
    es.onerror = () => {
      // Keep UI stable; users can refresh.
    }
    const handler = (evt: MessageEvent) => {
      // Not used.
      void evt
    }
    void handler
    const types = [
      'run.created',
      'subtasks.suggested',
      'subtasks.confirmed',
      'step.started',
      'step.completed',
      'step.invalidated',
      'retrieval.started',
      'retrieval.web_search',
      'retrieval.web_search_failed',
      'retrieval.card',
      'retrieval.completed',
      'summary.generated',
      'final.answer',
      'run.completed',
      'run.failed',
      'rerun.requested',
    ]
    for (const t of types) {
      es.addEventListener(t, (e) => {
        const me = e as MessageEvent
        setEvents((prev) => [...prev, { id: Number((e as any).lastEventId || 0), event: t, data: JSON.parse(me.data || '{}') }])
        // Refresh snapshot on meaningful state changes.
        if (['subtasks.suggested', 'subtasks.confirmed', 'step.completed', 'final.answer', 'run.completed'].includes(t)) {
          getRun(run.run_id).then(setRun).catch(() => {})
        }
      })
    }
    return () => {
      es.close()
    }
  }, [run?.run_id])

  const retrievalBySubtask = run?.retrieval || {}
  const summariesByDoc = run?.summaries || {}

  function subtaskEvents(subtaskId?: string) {
    if (!subtaskId) return []
    return events.filter((e) => e.data?.subtask_id === subtaskId)
  }

  const stepStatus = useMemo(() => {
    if (!run) return { s1: 'idle', s2: 'idle', s3: 'idle', s4: 'idle' }
    const s1 = 'done'
    const s2 = run.status === 'waiting_confirm' ? 'pending' : run.current_step >= 2 ? 'active' : 'pending'
    const s3 = run.current_step >= 3 ? 'active' : 'pending'
    const s4 = run.current_step >= 4 ? 'active' : 'pending'
    return { s1, s2, s3, s4 }
  }, [run])

  async function onCreateRun() {
    setError(null)
    setEvents([])
    try {
      const created = await createRun(query)
      const snap = await getRun(created.run_id)
      setRun(snap)
    } catch (e: any) {
      setError(e?.message || String(e))
    }
  }

  function updateSubtask(idx: number, name: string) {
    if (!run) return
    const next = [...run.subtasks]
    next[idx] = { ...next[idx], name }
    setRun({ ...run, subtasks: next })
  }

  function addSubtask() {
    if (!run) return
    const st: Subtask = { name: '', order: nextOrder(run.subtasks) }
    setRun({ ...run, subtasks: [...run.subtasks, st] })
  }

  function removeSubtask(idx: number) {
    if (!run) return
    const next = run.subtasks.filter((_, i) => i !== idx)
    setRun({ ...run, subtasks: next.map((s, i) => ({ ...s, order: i })) })
  }

  async function onConfirm() {
    if (!run) return
    setError(null)
    try {
      const sanitized = run.subtasks
        .map((s, i) => ({ id: s.id, name: s.name.trim(), order: i }))
        .filter((s) => s.name.length > 0)
      await confirmSubtasks(run.run_id, sanitized)
      const snap = await getRun(run.run_id)
      setRun(snap)
    } catch (e: any) {
      setError(e?.message || String(e))
    }
  }

  async function onRerun(step: number) {
    if (!run) return
    setError(null)
    try {
      await rerunFromStep(run.run_id, step, 'user requested')
    } catch (e: any) {
      setError(e?.message || String(e))
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="relative isolate overflow-hidden">
        <div className="pointer-events-none absolute -top-32 left-1/2 h-80 w-[46rem] -translate-x-1/2 rounded-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-cyan-300/50 via-sky-200/20 to-transparent blur-3xl" />
        <div className="pointer-events-none absolute right-10 top-40 h-64 w-64 rounded-full bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-emerald-200/60 via-slate-100/30 to-transparent blur-2xl" />
        <div className="mx-auto max-w-6xl px-6 pb-16 pt-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 text-sm font-semibold text-white">wp</div>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">wisdomprompt</h1>
                <div className="text-xs text-slate-500">Semantic prompt intelligence, refined live.</div>
              </div>
            </div>
            {run?.run_id ? (
              <div className="rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-xs text-slate-500 shadow-sm">run: {run.run_id}</div>
            ) : null}
          </div>

          <div className="mt-12 grid grid-cols-1 gap-10 lg:grid-cols-[1.2fr_0.8fr]">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-xs font-medium text-slate-600 shadow-sm">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                Live retrieval + synthesis workflow
              </div>
              <h2 className="mt-5 text-4xl font-semibold leading-[1.05] text-slate-900 sm:text-5xl">
                Orchestrate knowledge with a calm, modern AI flow.
              </h2>
              <p className="mt-5 max-w-xl text-base text-slate-600 sm:text-lg">
                Break down complex prompts into subtasks, watch retrieval unfold, and refine answers step-by-step. Every stage stays editable,
                auditable, and streaming in real time.
              </p>
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <a
                  href="#step-1"
                  className="rounded-full bg-slate-900 px-5 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-800"
                >
                  Start a run
                </a>
                <div className="rounded-full border border-slate-200 bg-white/70 px-4 py-2 text-xs text-slate-500">
                  4 steps • Milvus + web fallback
                </div>
              </div>
            </div>
            <div className="rounded-3xl border border-slate-200 bg-white/70 p-6 shadow-lg shadow-slate-200/60 backdrop-blur">
              <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Progressive Flow</div>
              <div className="mt-4 space-y-4">
                {[
                  { label: 'Step 1', title: 'Query → Subtasks', status: 'ready' },
                  { label: 'Step 2', title: 'Retrieval + Sources', status: canStep2 ? 'live' : 'locked' },
                  { label: 'Step 3', title: 'Synthesis Cards', status: canStep3 ? 'live' : 'locked' },
                  { label: 'Step 4', title: 'Final Answer', status: canStep4 ? 'live' : 'locked' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white px-4 py-3 shadow-sm">
                    <div>
                      <div className="text-xs text-slate-500">{item.label}</div>
                      <div className="text-sm font-medium text-slate-900">{item.title}</div>
                    </div>
                    <div
                      className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                        item.status === 'live'
                          ? 'bg-emerald-100 text-emerald-700'
                          : item.status === 'ready'
                            ? 'bg-sky-100 text-sky-700'
                            : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {item.status}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-6xl px-6 pb-20">
        <section
          id="step-1"
          className="rounded-3xl border border-slate-200 bg-white/80 p-6 shadow-lg shadow-slate-200/60 backdrop-blur"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Step 1</div>
              <div className="text-base font-semibold text-slate-900">Query → Subtasks</div>
            </div>
            <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-500">Editable + confirm</div>
          </div>
          <div className="mt-4 flex flex-col gap-4 lg:flex-row">
            <textarea
              className="min-h-[120px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 shadow-sm focus:border-slate-400 focus:outline-none"
              placeholder="Describe the knowledge you want to compile..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button
              className="h-[120px] w-full rounded-2xl bg-slate-900 text-sm font-medium text-white shadow-md transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 lg:w-40"
              onClick={onCreateRun}
              disabled={!query.trim()}
            >
              Run Step 1
            </button>
          </div>

          {run ? (
            <div className="mt-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm text-slate-600">Subtasks (editable; confirm to continue)</div>
                <button
                  className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:text-slate-800"
                  onClick={() => onRerun(1)}
                  disabled={!run}
                >
                  Rerun from Step 1
                </button>
              </div>

              <div className="mt-4 space-y-3">
                {run.subtasks.map((s, idx) => (
                  <div key={idx} className="flex flex-col gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm sm:flex-row sm:items-center">
                    <input
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 focus:border-slate-400 focus:outline-none"
                      value={s.name}
                      onChange={(e) => updateSubtask(idx, e.target.value)}
                    />
                    <button
                      className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                      onClick={() => removeSubtask(idx)}
                      disabled={run.subtasks.length <= 1}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <button
                  className="rounded-full border border-slate-200 px-4 py-2 text-xs text-slate-600 transition hover:border-slate-300 hover:text-slate-800"
                  onClick={addSubtask}
                >
                  Add subtask
                </button>
                <button
                  className="rounded-full bg-emerald-500 px-4 py-2 text-xs font-medium text-white shadow-sm transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={onConfirm}
                  disabled={!canConfirm}
                >
                  Confirm & Run Steps 2-4
                </button>
              </div>
            </div>
          ) : null}
        </section>

        <div className="mt-10 grid grid-cols-1 gap-6">
          <section className="rounded-3xl border border-slate-200 bg-white/80 p-6 shadow-lg shadow-slate-200/60 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Step 2</div>
                <div className="text-base font-semibold text-slate-900">Retrieval (Milvus → Web fallback)</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={() => onRerun(2)}
                  disabled={!canStep2}
                >
                  Rerun from Step 2
                </button>
                <button
                  className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={() => onRerun(3)}
                  disabled={!canStep3}
                >
                  Rerun from Step 3
                </button>
              </div>
            </div>

            {canStep2 ? (
              <div className="mt-5 space-y-4">
                {run?.subtasks.map((st) => (
                  <details key={st.id || st.order} className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm" open={canStep2}>
                    <summary className="cursor-pointer text-sm font-semibold text-slate-800">
                      {st.name || '(empty)'}
                    </summary>
                    <div className="mt-3 space-y-3">
                      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2">
                        <div className="text-xs font-semibold text-slate-700">Search process</div>
                        <div className="mt-1 space-y-1 text-[11px] text-slate-500">
                          {subtaskEvents(st.id)
                            .filter((e) => ['retrieval.started', 'retrieval.web_search', 'retrieval.web_search_failed', 'retrieval.completed'].includes(e.event))
                            .slice(-30)
                            .map((e, idx) => (
                              <div key={idx}>
                                <span className="text-slate-400">{e.event}</span> {JSON.stringify(e.data)}
                              </div>
                            ))}
                          {subtaskEvents(st.id).length === 0 ? <div className="text-slate-400">No activity yet.</div> : null}
                        </div>
                      </div>

                      {(retrievalBySubtask[st.id || ''] || []).map((card: any) => (
                        <div key={card.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="text-sm font-semibold text-slate-900">{card.title || 'Untitled'}</div>
                            <div className="text-xs text-slate-500">
                              {card.source?.provider || 'unknown'}
                              {card.source?.url ? (
                                <a className="ml-2 text-sky-700 hover:underline" href={card.source.url} target="_blank">
                                  link
                                </a>
                              ) : null}
                            </div>
                          </div>
                          <div className="mt-2 whitespace-pre-wrap text-xs text-slate-600">{card.content}</div>
                        </div>
                      ))}
                      {(retrievalBySubtask[st.id || ''] || []).length === 0 ? (
                        <div className="text-xs text-slate-400">No cards yet (watch events).</div>
                      ) : null}
                    </div>
                  </details>
                ))}
              </div>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                Step 2 unlocks after confirming subtasks.
              </div>
            )}
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white/80 p-6 shadow-lg shadow-slate-200/60 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Step 3</div>
                <div className="text-base font-semibold text-slate-900">Synthesis Summaries</div>
              </div>
              <button
                className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                onClick={() => onRerun(3)}
                disabled={!canStep3}
              >
                Rerun from Step 3
              </button>
            </div>
            {canStep3 ? (
              <div className="mt-5 space-y-4">
                {run?.subtasks.map((st) => (
                  <details key={st.id || st.order} className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm" open={canStep3}>
                    <summary className="cursor-pointer text-sm font-semibold text-slate-800">
                      {st.name || '(empty)'}
                    </summary>
                    <div className="mt-3 space-y-3">
                      {(retrievalBySubtask[st.id || ''] || []).map((card: any) => (
                        <div key={card.id} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                          <div className="text-xs font-semibold text-slate-700">{card.title || 'Untitled'}</div>
                          {summariesByDoc[card.id] ? (
                            <div className="mt-2 whitespace-pre-wrap text-xs text-slate-600">{summariesByDoc[card.id]}</div>
                          ) : (
                            <div className="mt-2 text-xs text-slate-400">Summary pending.</div>
                          )}
                        </div>
                      ))}
                      {(retrievalBySubtask[st.id || ''] || []).length === 0 ? (
                        <div className="text-xs text-slate-400">No retrieval cards yet.</div>
                      ) : null}
                    </div>
                  </details>
                ))}
              </div>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                Step 3 will expand after retrieval finishes.
              </div>
            )}
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white/80 p-6 shadow-lg shadow-slate-200/60 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Step 4</div>
                <div className="text-base font-semibold text-slate-900">Final Answer</div>
              </div>
              <button
                className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                onClick={() => onRerun(4)}
                disabled={!canStep4}
              >
                Rerun from Step 4
              </button>
            </div>
            {canStep4 ? (
              <div className="mt-4 whitespace-pre-wrap rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm">
                {run?.final_answer || <span className="text-slate-400">No final answer yet.</span>}
              </div>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                Step 4 appears once synthesis is complete.
              </div>
            )}
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white/80 p-6 shadow-lg shadow-slate-200/60 backdrop-blur">
            <div className="text-base font-semibold text-slate-900">Live Events</div>
            <div className="mt-4 max-h-[280px] overflow-auto rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600">
              {events.length ? (
                <div className="space-y-2">
                  {events.slice(-200).map((e, idx) => (
                    <div key={idx} className="text-slate-600">
                      <span className="text-slate-400">#{e.id || idx}</span> <span className="text-slate-800">{e.event}</span>{' '}
                      <span className="text-slate-400">{JSON.stringify(e.data)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-slate-400">No events yet.</div>
              )}
            </div>
          </section>
        </div>

        {error ? <div className="mt-6 text-sm text-red-500">{error}</div> : null}
        <div className="mt-6 text-xs text-slate-400">step status: {JSON.stringify(stepStatus)}</div>
      </div>
    </div>
  )
}

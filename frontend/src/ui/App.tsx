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
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">wisdomprompt</h1>
          {run?.run_id ? <div className="text-xs text-slate-400">run: {run.run_id}</div> : null}
        </div>

        <div className="mt-6 rounded-lg border border-slate-800 bg-slate-900 p-4">
          <div className="text-sm font-medium">Step 1: Query → Subtasks</div>
          <div className="mt-3 flex gap-3">
            <textarea
              className="min-h-[88px] w-full rounded-md border border-slate-700 bg-slate-950 p-2 text-sm"
              placeholder="Enter your query..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button
              className="h-[88px] w-32 rounded-md bg-indigo-600 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
              onClick={onCreateRun}
              disabled={!query.trim()}
            >
              Run Step 1
            </button>
          </div>

          {run ? (
            <div className="mt-4">
              <div className="flex items-center justify-between">
                <div className="text-sm text-slate-300">Subtasks (editable; confirm to continue)</div>
                <div className="flex gap-2">
                  <button
                    className="rounded-md border border-slate-700 px-3 py-1 text-xs hover:bg-slate-800"
                    onClick={() => onRerun(1)}
                    disabled={!run}
                  >
                    Rerun from Step 1
                  </button>
                </div>
              </div>

              <div className="mt-3 space-y-2">
                {run.subtasks.map((s, idx) => (
                  <div key={idx} className="flex gap-2">
                    <input
                      className="w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm"
                      value={s.name}
                      onChange={(e) => updateSubtask(idx, e.target.value)}
                    />
                    <button
                      className="rounded-md border border-slate-700 px-2 text-xs hover:bg-slate-800"
                      onClick={() => removeSubtask(idx)}
                      disabled={run.subtasks.length <= 1}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>

              <div className="mt-3 flex items-center gap-2">
                <button className="rounded-md border border-slate-700 px-3 py-1 text-xs hover:bg-slate-800" onClick={addSubtask}>
                  Add subtask
                </button>
                <button
                  className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-medium hover:bg-emerald-500 disabled:opacity-50"
                  onClick={onConfirm}
                  disabled={!canConfirm}
                >
                  Confirm & Run Steps 2-4
                </button>
              </div>
            </div>
          ) : null}
        </div>

        {run ? (
          <div className="mt-6 grid grid-cols-1 gap-6">
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium">Step 2: Retrieval (Milvus → Web fallback)</div>
                <div className="flex gap-2">
                  <button className="rounded-md border border-slate-700 px-3 py-1 text-xs hover:bg-slate-800" onClick={() => onRerun(2)}>
                    Rerun from Step 2
                  </button>
                  <button className="rounded-md border border-slate-700 px-3 py-1 text-xs hover:bg-slate-800" onClick={() => onRerun(3)}>
                    Rerun from Step 3
                  </button>
                </div>
              </div>
              <div className="mt-3 space-y-3">
                {run.subtasks.map((st) => (
                  <details key={st.id || st.order} className="rounded-md border border-slate-800 bg-slate-950 p-3" open>
                    <summary className="cursor-pointer text-sm font-medium text-slate-200">
                      {st.name || '(empty)'}
                    </summary>
                    <div className="mt-3 space-y-2">
                      <div className="rounded-md border border-slate-800 bg-slate-900 p-2">
                        <div className="text-xs font-medium text-slate-200">Search process</div>
                        <div className="mt-1 space-y-1 text-[11px] text-slate-400">
                          {subtaskEvents(st.id)
                            .filter((e) => ['retrieval.started', 'retrieval.web_search', 'retrieval.web_search_failed', 'retrieval.completed'].includes(e.event))
                            .slice(-30)
                            .map((e, idx) => (
                              <div key={idx}>
                                <span className="text-slate-500">{e.event}</span> {JSON.stringify(e.data)}
                              </div>
                            ))}
                          {subtaskEvents(st.id).length === 0 ? <div className="text-slate-500">No activity yet.</div> : null}
                        </div>
                      </div>

                      {(retrievalBySubtask[st.id || ''] || []).map((card: any) => (
                        <div key={card.id} className="rounded-md border border-slate-800 bg-slate-900 p-3">
                          <div className="flex items-center justify-between gap-3">
                            <div className="text-sm font-medium">{card.title || 'Untitled'}</div>
                            <div className="text-xs text-slate-400">
                              {card.source?.provider || 'unknown'}
                              {card.source?.url ? (
                                <a className="ml-2 text-indigo-400 hover:underline" href={card.source.url} target="_blank">
                                  link
                                </a>
                              ) : null}
                            </div>
                          </div>
                          <div className="mt-2 whitespace-pre-wrap text-xs text-slate-300">{card.content}</div>
                          {summariesByDoc[card.id] ? (
                            <div className="mt-3 rounded-md border border-slate-800 bg-slate-950 p-2">
                              <div className="text-xs font-medium text-slate-200">Step 3 summary</div>
                              <div className="mt-1 whitespace-pre-wrap text-xs text-slate-300">{summariesByDoc[card.id]}</div>
                            </div>
                          ) : null}
                        </div>
                      ))}
                      {(retrievalBySubtask[st.id || ''] || []).length === 0 ? (
                        <div className="text-xs text-slate-500">No cards yet (watch events).</div>
                      ) : null}
                    </div>
                  </details>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium">Step 4: Final Answer</div>
                <button className="rounded-md border border-slate-700 px-3 py-1 text-xs hover:bg-slate-800" onClick={() => onRerun(4)}>
                  Rerun from Step 4
                </button>
              </div>
              <div className="mt-3 whitespace-pre-wrap rounded-md border border-slate-800 bg-slate-950 p-3 text-sm">
                {run.final_answer || <span className="text-slate-500">No final answer yet.</span>}
              </div>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <div className="text-sm font-medium">Live Events</div>
              <div className="mt-3 max-h-[280px] overflow-auto rounded-md border border-slate-800 bg-slate-950 p-3 text-xs">
                {events.length ? (
                  <div className="space-y-2">
                    {events.slice(-200).map((e, idx) => (
                      <div key={idx} className="text-slate-300">
                        <span className="text-slate-500">#{e.id || idx}</span> <span className="text-slate-200">{e.event}</span>{' '}
                        <span className="text-slate-500">{JSON.stringify(e.data)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-slate-500">No events yet.</div>
                )}
              </div>
            </div>
          </div>
        ) : null}

        {error ? <div className="mt-6 text-sm text-red-400">{error}</div> : null}
        <div className="mt-6 text-xs text-slate-500">step status: {JSON.stringify(stepStatus)}</div>
      </div>
    </div>
  )
}

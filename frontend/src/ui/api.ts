export type Subtask = { id?: string; name: string; order: number }

export type RunCreated = {
  run_id: string
  status: string
  subtasks: Subtask[]
}

export type RunSnapshot = {
  run_id: string
  query: string
  status: string
  current_step: number
  subtasks: Subtask[]
  retrieval: Record<string, any[]>
  summaries: Record<string, string>
  final_answer?: string | null
}

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function createRun(query: string): Promise<RunCreated> {
  const r = await fetch(`${API_BASE}/api/runs`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!r.ok) throw new Error(`createRun failed: ${r.status}`)
  return r.json()
}

export async function getRun(runId: string): Promise<RunSnapshot> {
  const r = await fetch(`${API_BASE}/api/runs/${runId}`)
  if (!r.ok) throw new Error(`getRun failed: ${r.status}`)
  return r.json()
}

export async function confirmSubtasks(runId: string, subtasks: Subtask[]): Promise<void> {
  const r = await fetch(`${API_BASE}/api/runs/${runId}/subtasks/confirm`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ subtasks }),
  })
  if (!r.ok) throw new Error(`confirmSubtasks failed: ${r.status}`)
}

export async function rerunFromStep(runId: string, step: number, reason?: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/runs/${runId}/step/${step}/rerun`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ reason: reason || null }),
  })
  if (!r.ok) throw new Error(`rerun failed: ${r.status}`)
}

export function eventsUrl(runId: string): string {
  return `${API_BASE}/api/runs/${runId}/events`
}

import type { Message } from './types'

const BASE = 'http://localhost:8000'

export async function analyzeFood(file: File): Promise<string> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/api/analyze-food`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? 'Failed to analyze image')
  }
  const data = await res.json()
  return data.nutrition_label as string
}

export async function chat(messages: Message[], foodContext: string): Promise<string> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      food_context: foodContext,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? 'Failed to get reply')
  }
  const data = await res.json()
  return data.reply as string
}

export type ChatMessage = { role: 'user'|'assistant'|'system'; content: string }
export type UploadDoc = { id: string; title: string; page_count: number }

export async function listDocuments(): Promise<UploadDoc[]> {
  try {
    const res = await fetch('/api/documents')
    if (!res.ok) throw new Error(`listDocuments failed: ${res.status}`)
    const data = await res.json()
    return (data.items || [])
  } catch (err) {
    console.error('[listDocuments] error', err)
    throw err
  }
}

export async function uploadDocuments(files: File[]): Promise<UploadDoc[]> {
  console.log('[uploadDocuments] sending files:', files.map(f => ({ name: f.name, type: f.type, size: f.size })))
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  let res: Response
  try {
    res = await fetch('/api/documents', { method: 'POST', body: form })
  } catch (err) {
    console.error('[uploadDocuments] network error', err)
    throw err
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    console.error('[uploadDocuments] server error', { status: res.status, body: text })
    throw new Error(`Upload failed: ${res.status} ${text}`)
  }
  const data = await res.json()
  console.log('[uploadDocuments] success:', data)
  return data.documents
}

export function streamChat(body: {
  messages: ChatMessage[]
  document_ids?: string[]
  force_web?: boolean
}, onToken: (t: string) => void, onDone: (finalEnvelope: any) => void) {
  const ctrl = new AbortController()
  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: ctrl.signal,
  }).then(async res => {
    if (!res.ok || !res.body) throw new Error('Chat stream failed')
    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        if (part.startsWith('data: ')) {
          const payload = part.slice(6)
          // Attempt to parse JSON, but only treat as final envelope
          // if it's an object with expected keys. Primitive JSON like
          // numbers (e.g., "10.000") should be treated as tokens.
          let handled = false
          try {
            const parsed = JSON.parse(payload)
            if (
              parsed && typeof parsed === 'object' && !Array.isArray(parsed) &&
              (Object.prototype.hasOwnProperty.call(parsed, 'citations') ||
               Object.prototype.hasOwnProperty.call(parsed, 'sources'))
            ) {
              onDone(parsed)
              handled = true
            }
          } catch {
            // not JSON, fall through
          }
          if (!handled) {
            onToken(payload)
          }
        }
      }
    }
  }).catch(() => {/* ignore for MVP */})
  return () => ctrl.abort()
}

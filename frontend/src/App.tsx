import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Dropzone from './components/Dropzone'
import { uploadDocuments, streamChat, type ChatMessage, listDocuments } from './api'
import { FilePlus, Link2, ScrollText, Waypoints } from 'lucide-react'
import SourcesPanel from './components/SourcesPanel'

export default function App() {
  const [docs, setDocs] = useState<{id:string;title:string;page_count:number}[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [uploading, setUploading] = useState(false)
  const [answering, setAnswering] = useState(false)
  const [finalEnvelope, setFinalEnvelope] = useState<any | null>(null)
  const abortRef = useRef<(() => void) | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [mode, setMode] = useState<'auto'|'docs'|'web'>('auto')

  // Load existing documents on first render
  useEffect(() => {
    (async () => {
      try {
        const existing = await listDocuments()
        setDocs(existing)
      } catch (e) {
        // eslint-disable-next-line no-console
        console.error('[App] failed to list documents', e)
      }
    })()
  }, [])

  const onFiles = useCallback(async (files: File[]) => {
    setUploading(true)
    try {
      const res = await uploadDocuments(files)
      setDocs(prev => [...prev, ...res])
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error(e)
    } finally {
      setUploading(false)
    }
  }, [])

  const startChat = useCallback(() => {
    if (!input.trim()) return
    const newMsgs: ChatMessage[] = [...messages, { role: 'user', content: input.trim() }]
    setMessages(newMsgs)
    setInput('')
    setAnswering(true)
    setFinalEnvelope(null)
    const body = {
      messages: newMsgs,
      document_ids: mode === 'web' ? [] : (docs.length ? docs.map(d => d.id) : undefined),
      force_web: mode === 'web',
    }
    abortRef.current = streamChat(body, (tok) => {
      setMessages(curr => {
        const last = curr[curr.length-1]
        if (!last || last.role !== 'assistant') return [...curr, { role: 'assistant', content: tok }]
        const updated = [...curr]
        updated[updated.length-1] = { role: 'assistant', content: last.content + tok }
        return updated
      })
    }, (env) => {
      setFinalEnvelope(env)
      setAnswering(false)
      abortRef.current = null
    })
  }, [docs, input, messages, mode])

  const disabled = uploading || answering

  const docStats = useMemo(() => `${docs.length} document(s)`, [docs])

  return (
    <div className="h-full grid grid-rows-[auto,1fr]">
      <header className="border-b bg-white px-4 py-2 flex items-center gap-4">
        <h1 className="font-semibold">RAG PDF/Web QA</h1>
        <div className="text-xs text-gray-500">{docStats}</div>
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => setMode('docs')} className={`px-2 py-1 text-sm border rounded flex items-center gap-1 ${mode==='docs'?'bg-gray-100':''}`}><ScrollText size={16}/> Answer from Docs</button>
          <button onClick={() => setMode('web')} className={`px-2 py-1 text-sm border rounded flex items-center gap-1 ${mode==='web'?'bg-gray-100':''}`}><Link2 size={16}/> Answer from Web</button>
          <button onClick={() => setMode('auto')} className={`px-2 py-1 text-sm border rounded flex items-center gap-1 ${mode==='auto'?'bg-gray-100':''}`}><Waypoints size={16}/> Let the bot decide</button>
        </div>
      </header>
      <main className="grid grid-cols-1 md:grid-cols-[1fr,360px] h-full">
        <section className="p-4 flex flex-col gap-3 overflow-y-auto">
          <Dropzone disabled={disabled} onFiles={onFiles} />
          <div>
            <input
              className="w-full border rounded px-3 py-2"
              placeholder={uploading ? 'Processing...' : 'Ask a question'}
              disabled={disabled}
              value={input}
              onChange={(e)=>setInput(e.target.value)}
              onKeyDown={(e)=>{ if(e.key==='Enter') startChat() }}
            />
            <div className="mt-2 flex gap-2">
              <button disabled={disabled} onClick={startChat} className="px-3 py-2 border rounded bg-black text-white text-sm">Send</button>
            </div>
          </div>
          <div className="flex-1 space-y-3">
            {messages.map((m,i)=> (
              <div key={i} className={`p-3 rounded ${m.role==='user'?'bg-blue-50':'bg-gray-100'}`}>
                <div className="text-xs text-gray-500 mb-1">{m.role}</div>
                <div className="whitespace-pre-wrap break-words">{m.content}</div>
              </div>
            ))}
          </div>
        </section>
        <aside className="border-l bg-white p-3 overflow-y-auto">
          <SourcesPanel envelope={finalEnvelope} docs={docs}/>
          <div className="mt-4">
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              multiple
              className="hidden"
              onChange={(e)=>{
                const files = Array.from(e.target.files || [])
                if (files.length) onFiles(files)
                // reset so the same file can be selected again
                e.currentTarget.value = ''
              }}
            />
            <button
              className="px-2 py-1 text-sm border rounded flex items-center gap-1"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
            >
              <FilePlus size={16}/> Upload
            </button>
            <div className="mt-3">
              <div className="text-xs font-semibold text-gray-600 mb-1">Documents</div>
              {docs.length === 0 ? (
                <div className="text-xs text-gray-500">No documents yet</div>
              ) : (
                <ul className="space-y-1">
                  {docs.map((d) => (
                    <li key={d.id} className="text-sm flex items-center justify-between gap-2">
                      <span className="truncate" title={d.title}>{d.title}</span>
                      <span className="text-xs text-gray-500 whitespace-nowrap">{d.page_count} pages</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}

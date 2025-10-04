import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Dropzone from './components/Dropzone'
import { uploadDocuments, streamChat, type ChatMessage, listDocuments, deleteDocument } from './api'
import { FilePlus, Link2, ScrollText, Waypoints, Send, Sparkles, Trash2 } from 'lucide-react'
import SourcesPanel from './components/SourcesPanel'
import ReactMarkdown from 'react-markdown'

// Helper to render message content with markdown, images, and highlighted citations
function renderWithCitations(content: string) {
  console.log('[renderWithCitations] content:', content)

  return (
    <div>
      <ReactMarkdown
        components={{
          // Style images
          img: ({ src, alt, ...props }) => {
            console.log('[ReactMarkdown img]', src, alt)
            return <img src={src} alt={alt || 'Image'} className="max-w-full max-h-96 rounded-lg shadow-md my-2" {...props} />
          },
          // Style links
          a: ({ href, children }) => (
            <a href={href} className="text-blue-600 underline" target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
          // Bold text
          strong: ({ children }) => <strong className="font-bold">{children}</strong>,
          // Paragraphs with citation highlighting
          p: ({ children }) => {
            const text = String(children)
            const parts = text.split(/(\[\d+\])/g)
            const hasCitations = parts.some(p => /\[\d+\]/.test(p))

            if (hasCitations) {
              return (
                <p className="mb-2">
                  {parts.map((part, i) => {
                    if (/\[\d+\]/.test(part)) {
                      return (
                        <span key={i} className="inline-flex items-center mx-0.5 px-1.5 py-0.5 text-xs font-semibold bg-blue-100 text-blue-700 rounded">
                          {part}
                        </span>
                      )
                    }
                    return <span key={i}>{part}</span>
                  })}
                </p>
              )
            }
            return <p className="mb-2">{children}</p>
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

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
  const messagesEndRef = useRef<HTMLDivElement>(null)

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

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
    <div className="h-full grid grid-rows-[auto,1fr] bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Modern Header with Gradient */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="border-b bg-white/80 backdrop-blur-sm px-6 py-3 flex items-center gap-4 shadow-sm"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="text-blue-600" size={24} />
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            RAG Assistant
          </h1>
        </div>
        <div className="text-sm text-gray-600 px-2 py-1 bg-gray-100 rounded-full">{docStats}</div>
        <div className="ml-auto flex items-center gap-2">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setMode('docs')}
            className={`px-3 py-2 text-sm rounded-lg flex items-center gap-2 transition-all ${
              mode === 'docs'
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-200'
                : 'bg-white border border-gray-200 text-gray-700 hover:border-blue-300'
            }`}
          >
            <ScrollText size={16} /> Docs
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setMode('web')}
            className={`px-3 py-2 text-sm rounded-lg flex items-center gap-2 transition-all ${
              mode === 'web'
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-200'
                : 'bg-white border border-gray-200 text-gray-700 hover:border-purple-300'
            }`}
          >
            <Link2 size={16} /> Web
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setMode('auto')}
            className={`px-3 py-2 text-sm rounded-lg flex items-center gap-2 transition-all ${
              mode === 'auto'
                ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-200'
                : 'bg-white border border-gray-200 text-gray-700 hover:border-blue-300'
            }`}
          >
            <Waypoints size={16} /> Auto
          </motion.button>
        </div>
      </motion.header>

      <main className="grid grid-cols-1 md:grid-cols-[1fr,400px] h-full overflow-hidden">
        {/* Chat Section */}
        <section className="flex flex-col h-full">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            <Dropzone disabled={disabled} onFiles={onFiles} />

            <AnimatePresence mode="popLayout">
              {messages.map((m, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.3 }}
                  className={`p-4 rounded-xl shadow-sm ${
                    m.role === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white ml-auto max-w-[80%]'
                      : 'bg-white border border-gray-200 mr-auto max-w-[85%]'
                  }`}
                >
                  <div className={`text-xs font-semibold mb-2 ${m.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                    {m.role === 'user' ? 'You' : 'Assistant'}
                  </div>
                  <div className={m.role === 'user' ? 'whitespace-pre-wrap break-words leading-relaxed' : 'break-words leading-relaxed'}>
                    {m.role === 'assistant' ? renderWithCitations(m.content) : m.content}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {answering && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2 text-gray-500 text-sm"
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                >
                  <Sparkles size={16} />
                </motion.div>
                Thinking...
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 bg-white border-t">
            <div className="flex gap-2">
              <input
                className="flex-1 border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder={uploading ? 'Processing documents...' : 'Ask me anything...'}
                disabled={disabled}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    startChat()
                  }
                }}
              />
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                disabled={disabled}
                onClick={startChat}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-medium shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <Send size={18} />
                Send
              </motion.button>
            </div>
          </div>
        </section>

        {/* Sidebar */}
        <aside className="border-l bg-white/80 backdrop-blur-sm p-4 overflow-y-auto">
          <SourcesPanel envelope={finalEnvelope} docs={docs} />

          <div className="mt-6">
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              multiple
              className="hidden"
              onChange={(e) => {
                const files = Array.from(e.target.files || [])
                if (files.length) onFiles(files)
                e.currentTarget.value = ''
              }}
            />
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full px-4 py-2 text-sm border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center gap-2 hover:border-blue-500 hover:bg-blue-50 transition-all"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
            >
              <FilePlus size={16} /> Upload PDFs
            </motion.button>

            <div className="mt-4">
              <div className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider">Documents</div>
              {docs.length === 0 ? (
                <div className="text-sm text-gray-400 italic">No documents uploaded yet</div>
              ) : (
                <ul className="space-y-2">
                  <AnimatePresence>
                    {docs.map((d) => (
                      <motion.li
                        key={d.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        className="text-sm flex items-center justify-between gap-2 p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
                      >
                        <span className="truncate font-medium flex-1" title={d.title}>
                          {d.title}
                        </span>
                        <span className="text-xs text-gray-500 whitespace-nowrap bg-white px-2 py-1 rounded">
                          {d.page_count}p
                        </span>
                        <motion.button
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          onClick={async () => {
                            try {
                              await deleteDocument(d.id)
                              setDocs(prev => prev.filter(doc => doc.id !== d.id))
                            } catch (err) {
                              console.error('Delete failed:', err)
                            }
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1 text-red-500 hover:bg-red-50 rounded transition-all"
                          title="Delete document"
                        >
                          <Trash2 size={14} />
                        </motion.button>
                      </motion.li>
                    ))}
                  </AnimatePresence>
                </ul>
              )}
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}

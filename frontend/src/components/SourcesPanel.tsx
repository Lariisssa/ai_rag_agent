import React from 'react'

type Doc = { id: string; title: string; page_count: number }

type Props = {
  envelope: any | null
  docs: Doc[]
}

export default function SourcesPanel({ envelope, docs }: Props) {
  if (!envelope) return (
    <div>
      <h3 className="font-medium mb-2">Sources</h3>
      <p className="text-sm text-gray-500">No sources yet.</p>
    </div>
  )
  const { sources } = envelope as { sources?: { type: 'doc'|'web', items: any[] } }
  return (
    <div>
      <h3 className="font-medium mb-2">Sources</h3>
      {!sources || sources.items.length===0 ? (
        <p className="text-sm text-gray-500">No sources found.</p>
      ) : sources.type === 'doc' ? (
        <div className="space-y-2">
          {sources.items.map((it, idx) => (
            <div key={idx} className="border rounded p-2">
              <div className="text-sm font-medium">{it.title} — p.{it.page}</div>
              <div className="text-xs text-gray-500">similarity: {it.similarity?.toFixed?.(3) ?? it.similarity}</div>
              <div className="text-sm line-clamp-3 mt-1">{it.snippet}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {sources.items.map((it, idx) => (
            <div key={idx} className="border rounded p-2">
              <a className="text-sm font-medium text-blue-600" href={it.url} target="_blank" rel="noreferrer">{it.title}</a>
              <div className="text-xs text-gray-500">{new URL(it.url).hostname}</div>
              <div className="text-sm line-clamp-3 mt-1">{it.snippet}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ImageIcon, X, ExternalLink, FileText } from 'lucide-react'

type Doc = { id: string; title: string; page_count: number }

type Image = {
  id: string
  file_url: string
  position: any
  dimensions: any
}

type Props = {
  envelope: any | null
  docs: Doc[]
}

export default function SourcesPanel({ envelope, docs }: Props) {
  const [selectedImage, setSelectedImage] = useState<string | null>(null)

  if (!envelope) return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wider">Sources</h3>
      <p className="text-sm text-gray-400 italic">No sources yet.</p>
    </div>
  )

  const { sources } = envelope as { sources?: { type: 'doc'|'web', items: any[] } }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wider">Sources</h3>
      {!sources || sources.items.length===0 ? (
        <p className="text-sm text-gray-400 italic">No sources found.</p>
      ) : sources.type === 'doc' ? (
        <div className="space-y-3">
          <AnimatePresence>
            {sources.items.map((it, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="border border-gray-200 rounded-xl p-3 bg-gradient-to-br from-white to-gray-50 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-start gap-2">
                  <FileText className="text-blue-500 flex-shrink-0 mt-1" size={16} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-gray-800">{it.title}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-500">Page {it.page}</span>
                      <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
                        {(it.similarity * 100).toFixed(1)}% match
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 line-clamp-2 mt-2">{it.snippet}</div>

                    {/* Images Section */}
                    {it.images && it.images.length > 0 && (
                      <div className="mt-3">
                        <div className="flex items-center gap-1 text-xs text-gray-600 mb-2">
                          <ImageIcon size={12} />
                          <span className="font-medium">{it.images.length} image{it.images.length > 1 ? 's' : ''}</span>
                        </div>
                        <div className="flex gap-2 flex-wrap">
                          {it.images.map((img: Image) => (
                            <motion.div
                              key={img.id}
                              whileHover={{ scale: 1.05 }}
                              whileTap={{ scale: 0.95 }}
                              className="border-2 border-gray-200 rounded-lg overflow-hidden cursor-pointer hover:border-blue-400 transition-colors"
                              onClick={() => setSelectedImage(img.file_url)}
                            >
                              <img
                                src={img.file_url}
                                alt="Page image"
                                className="h-20 w-auto object-cover"
                              />
                            </motion.div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      ) : (
        <div className="space-y-3">
          <AnimatePresence>
            {sources.items.map((it, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="border border-gray-200 rounded-xl p-3 bg-gradient-to-br from-white to-purple-50 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-start gap-2">
                  <ExternalLink className="text-purple-500 flex-shrink-0 mt-1" size={16} />
                  <div className="flex-1 min-w-0">
                    <a
                      className="text-sm font-semibold text-purple-600 hover:text-purple-700 hover:underline"
                      href={it.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {it.title}
                    </a>
                    <div className="text-xs text-gray-500 mt-1">{new URL(it.url).hostname}</div>
                    <div className="text-sm text-gray-600 line-clamp-2 mt-2">{it.snippet}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Image Modal */}
      <AnimatePresence>
        {selectedImage && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50 p-4 backdrop-blur-sm"
            onClick={() => setSelectedImage(null)}
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="relative max-w-4xl max-h-full"
            >
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setSelectedImage(null)}
                className="absolute -top-12 right-0 text-white hover:text-gray-300 bg-white/10 rounded-full p-2"
              >
                <X size={24} />
              </motion.button>
              <img
                src={selectedImage}
                alt="Full size"
                className="max-w-full max-h-[90vh] object-contain rounded-lg shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

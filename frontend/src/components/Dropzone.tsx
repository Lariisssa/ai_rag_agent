import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Upload, FileText } from 'lucide-react'

type Props = {
  disabled?: boolean
  onFiles: (files: File[]) => void
}

export default function Dropzone({ disabled, onFiles }: Props) {
  const [isDragging, setIsDragging] = useState(false)

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (disabled) return
    const files = Array.from(e.dataTransfer.files)
    onFiles(files)
  }

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    if (!disabled) setIsDragging(true)
  }

  const onDragLeave = () => {
    setIsDragging(false)
  }

  return (
    <motion.div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      animate={{
        scale: isDragging ? 1.02 : 1,
        borderColor: isDragging ? 'rgb(59 130 246)' : 'rgb(209 213 219)',
      }}
      className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
        disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-blue-400'
      } ${isDragging ? 'bg-blue-50 border-blue-500' : 'bg-white'}`}
    >
      <div className="flex flex-col items-center gap-2">
        <motion.div
          animate={{ y: isDragging ? -5 : 0 }}
          transition={{ type: 'spring', stiffness: 300 }}
        >
          {isDragging ? (
            <FileText className="text-blue-600" size={32} />
          ) : (
            <Upload className="text-gray-400" size={32} />
          )}
        </motion.div>
        <div>
          <p className={`text-sm font-medium ${isDragging ? 'text-blue-600' : 'text-gray-700'}`}>
            {isDragging ? 'Drop your PDFs here!' : 'Drop PDFs here'}
          </p>
          <p className="text-xs text-gray-500 mt-1">or use the Upload button in the sidebar</p>
        </div>
      </div>
    </motion.div>
  )
}

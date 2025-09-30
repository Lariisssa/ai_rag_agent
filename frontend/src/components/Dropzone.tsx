import React from 'react'

type Props = {
  disabled?: boolean
  onFiles: (files: File[]) => void
}

export default function Dropzone({ disabled, onFiles }: Props) {
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (disabled) return
    const files = Array.from(e.dataTransfer.files)
    onFiles(files)
  }
  return (
    <div
      onDragOver={e => e.preventDefault()}
      onDrop={onDrop}
      className={`border-2 border-dashed rounded p-4 text-center ${disabled ? 'opacity-50' : ''}`}
    >
      <p className="text-sm text-gray-600">Drop PDFs here or use the button below</p>
    </div>
  )
}

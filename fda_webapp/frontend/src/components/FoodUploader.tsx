import { useRef, useCallback } from 'react'
import { Camera, ImagePlus, Loader2, ClipboardPaste } from 'lucide-react'
import { useClipboardPaste } from '../hooks/useClipboardPaste'

interface Props {
  onUpload: (file: File) => void
  isLoading: boolean
  large?: boolean
}

export default function FoodUploader({ onUpload, isLoading, large = false }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  // Window-level paste listener — active on the empty state (large=true) when not loading
  useClipboardPaste(onUpload, isLoading || !large)

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) { onUpload(file); e.target.value = '' }
    },
    [onUpload],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const file = e.dataTransfer.files?.[0]
      if (file?.type.startsWith('image/')) onUpload(file)
    },
    [onUpload],
  )

  if (large) {
    return (
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload a food photo"
        className={`w-full max-w-md border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all select-none
          ${isLoading
            ? 'border-green-300 bg-green-50 cursor-not-allowed'
            : 'border-gray-300 hover:border-green-400 hover:bg-green-50/40 bg-white'}`}
        onClick={() => !isLoading && inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onKeyDown={(e) => e.key === 'Enter' && !isLoading && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleChange}
          disabled={isLoading}
        />

        {isLoading ? (
          <div className="flex flex-col items-center gap-3 text-green-600">
            <Loader2 size={40} className="animate-spin" />
            <p className="font-medium">Analyzing your food…</p>
            <p className="text-sm text-green-500">Generating nutrition facts</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 text-gray-500">
            <div className="bg-gray-100 p-4 rounded-full">
              <Camera size={32} className="text-gray-400" />
            </div>
            <div>
              <p className="font-semibold text-gray-700">Drop a photo or click to browse</p>
              <p className="text-sm mt-1">JPG · PNG · HEIC · or take a photo on mobile</p>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-400 bg-gray-50 border border-gray-200 rounded-lg px-3 py-1.5 mt-1">
              <ClipboardPaste size={13} />
              <span>Or paste from clipboard</span>
              <kbd className="ml-1 bg-white border border-gray-200 rounded px-1 font-mono text-[10px]">Ctrl+V</kbd>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Compact mid-chat button
  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleChange}
        disabled={isLoading}
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={isLoading}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-green-600 hover:bg-green-50 border border-gray-200 hover:border-green-300 px-3 py-2 rounded-xl transition-colors disabled:opacity-50"
        aria-label="Upload another food photo"
      >
        {isLoading ? <Loader2 size={15} className="animate-spin" /> : <ImagePlus size={15} />}
        <span>{isLoading ? 'Analyzing…' : 'New photo'}</span>
      </button>
    </>
  )
}

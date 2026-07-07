import { useState, useRef } from 'react'
import { Send, ClipboardPaste } from 'lucide-react'

const SUGGESTIONS = [
  'Is this healthy for me?',
  'How many calories is this?',
  'What are healthier alternatives?',
  'Does this fit a low-carb diet?',
  'How much protein does this have?',
]

interface Props {
  onSend: (text: string) => void
  onPasteImage: (file: File) => void
  disabled: boolean
  placeholder?: string
}

export default function ChatInput({
  onSend,
  onPasteImage,
  disabled,
  placeholder = 'Ask about your food…',
}: Props) {
  const [text, setText] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(true)
  const [pasteFlash, setPasteFlash] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const send = () => {
    if (!text.trim() || disabled) return
    onSend(text.trim())
    setText('')
    setShowSuggestions(false)
    textareaRef.current?.focus()
  }

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items
    if (!items) return
    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile()
        if (file) {
          e.preventDefault()
          // Flash the border to give feedback
          setPasteFlash(true)
          setTimeout(() => setPasteFlash(false), 600)
          onPasteImage(file)
          return
        }
      }
    }
    // Non-image paste — let it fall through normally (text)
  }

  const handleSuggestion = (s: string) => {
    onSend(s)
    setShowSuggestions(false)
  }

  return (
    <div className="space-y-2">
      {showSuggestions && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => handleSuggestion(s)}
              disabled={disabled}
              className="text-xs bg-white border border-gray-200 text-gray-600 hover:border-green-400 hover:text-green-700 hover:bg-green-50 px-3 py-1.5 rounded-full transition-colors disabled:opacity-40"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div
        className={`flex items-end gap-2 bg-white border rounded-2xl shadow-sm px-4 py-2 transition-all
          ${pasteFlash
            ? 'border-green-500 ring-2 ring-green-300'
            : 'border-gray-200 focus-within:border-green-400 focus-within:ring-1 focus-within:ring-green-200'
          }`}
      >
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          onPaste={handlePaste}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          aria-label="Chat message"
          className="flex-1 resize-none bg-transparent text-sm text-gray-800 placeholder-gray-400 outline-none py-1 max-h-32 disabled:opacity-50"
        />
        <button
          onClick={send}
          disabled={disabled || !text.trim()}
          aria-label="Send message"
          className="flex-shrink-0 w-8 h-8 bg-green-500 hover:bg-green-600 disabled:bg-gray-200 text-white rounded-xl flex items-center justify-center transition-colors mb-0.5"
        >
          <Send size={15} />
        </button>
      </div>

      <p className="text-xs text-gray-400 text-center flex items-center justify-center gap-2">
        <span>Enter to send · Shift+Enter for new line</span>
        <span className="text-gray-300">·</span>
        <span className="flex items-center gap-1">
          <ClipboardPaste size={11} />
          Paste image with
          <kbd className="bg-gray-100 border border-gray-200 rounded px-1 font-mono text-[10px]">Ctrl+V</kbd>
        </span>
      </p>
    </div>
  )
}

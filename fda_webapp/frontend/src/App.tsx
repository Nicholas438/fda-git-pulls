import { useState, useCallback, useEffect, useRef } from 'react'
import Header from './components/Header'
import FoodUploader from './components/FoodUploader'
import ChatMessages from './components/ChatMessages'
import ChatInput from './components/ChatInput'
import { analyzeFood, chat } from './api'
import type { Message } from './types'

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [foodContext, setFoodContext] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isReplying, setIsReplying] = useState(false)
  const [hasFood, setHasFood] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isReplying, isAnalyzing])

  const handleUpload = useCallback(async (file: File) => {
    const imageUrl = URL.createObjectURL(file)
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: "Here's a photo of my food — can you give me the nutrition facts?",
      imageUrl,
    }
    setMessages((prev) => [...prev, userMsg])
    setIsAnalyzing(true)

    try {
      const label = await analyzeFood(file)
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', content: label },
      ])
      setFoodContext(label)
      setHasFood(true)
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: "Sorry, I couldn't analyze that image. Please try a clearer photo. 🍽️",
        },
      ])
    } finally {
      setIsAnalyzing(false)
    }
  }, [])

  const handleSend = useCallback(
    async (text: string) => {
      const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: text }
      const nextMessages = [...messages, userMsg]
      setMessages(nextMessages)
      setIsReplying(true)

      try {
        const reply = await chat(nextMessages, foodContext)
        setMessages((prev) => [
          ...prev,
          { id: crypto.randomUUID(), role: 'assistant', content: reply },
        ])
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: "I'm having trouble responding right now. Please try again.",
          },
        ])
      } finally {
        setIsReplying(false)
      }
    },
    [messages, foodContext],
  )

  const handleReset = useCallback(() => {
    setMessages([])
    setFoodContext('')
    setHasFood(false)
  }, [])

  const isEmpty = messages.length === 0
  const busy = isAnalyzing || isReplying

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Header onReset={handleReset} hasFood={hasFood} />

      <main className="flex-1 overflow-hidden flex flex-col max-w-3xl w-full mx-auto px-4 pb-4">
        {isEmpty ? (
          /* ── Empty state ── */
          <div className="flex-1 flex flex-col items-center justify-center gap-8 py-12">
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-bold text-gray-800">What are you eating today?</h2>
              <p className="text-gray-500 max-w-sm">
                Upload a photo of your meal and get an instant FDA-style Nutrition Facts label.
                Then ask me anything about it.
              </p>
            </div>
            <FoodUploader onUpload={handleUpload} isLoading={isAnalyzing} large />
          </div>
        ) : (
          /* ── Chat view ── */
          <>
            <div className="flex-1 overflow-y-auto chat-scroll py-4 space-y-1">
              <ChatMessages messages={messages} isTyping={busy} />
              <div ref={bottomRef} />
            </div>

            <div className="pt-2 space-y-3">
              <FoodUploader onUpload={handleUpload} isLoading={isAnalyzing} />
              <ChatInput
                onSend={handleSend}
                onPasteImage={handleUpload}
                disabled={busy}
                placeholder="Ask me anything about this food…"
              />
            </div>
          </>
        )}
      </main>
    </div>
  )
}

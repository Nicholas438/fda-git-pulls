import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Salad, User } from 'lucide-react'
import type { Message } from '../types'

interface Props {
  messages: Message[]
  isTyping: boolean
}

export default function ChatMessages({ messages, isTyping }: Props) {
  return (
    <div className="space-y-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {isTyping && (
        <div className="flex items-start gap-3">
          <AIAvatar />
          <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
            <div className="flex items-center gap-1 h-5">
              <span className="dot w-2 h-2 bg-green-400 rounded-full inline-block" />
              <span className="dot w-2 h-2 bg-green-400 rounded-full inline-block" />
              <span className="dot w-2 h-2 bg-green-400 rounded-full inline-block" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex items-start gap-3 justify-end">
        <div className="flex flex-col items-end gap-1 max-w-[80%]">
          {message.imageUrl && (
            <img
              src={message.imageUrl}
              alt="Food photo"
              className="rounded-2xl rounded-tr-sm max-w-xs max-h-60 object-cover shadow border border-gray-200"
            />
          )}
          <div className="bg-green-500 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm shadow-sm">
            <p className="text-sm leading-relaxed">{message.content}</p>
          </div>
        </div>
        <UserAvatar />
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3">
      <AIAvatar />
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm max-w-[85%] overflow-x-auto">
        <div className="prose prose-sm max-w-none text-gray-800
          prose-headings:font-bold prose-headings:text-gray-900
          prose-h2:text-base prose-h2:mt-2 prose-h2:mb-1
          prose-h3:text-sm prose-h3:mt-3 prose-h3:mb-1
          prose-p:my-1 prose-p:leading-relaxed
          prose-ul:my-1 prose-li:my-0.5
          prose-strong:text-gray-900
          prose-hr:my-2">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

function AIAvatar() {
  return (
    <div className="flex-shrink-0 w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center shadow-sm">
      <Salad size={16} />
    </div>
  )
}

function UserAvatar() {
  return (
    <div className="flex-shrink-0 w-8 h-8 bg-gray-200 text-gray-600 rounded-full flex items-center justify-center">
      <User size={16} />
    </div>
  )
}

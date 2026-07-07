import { Salad, RotateCcw } from 'lucide-react'

interface Props {
  onReset: () => void
  hasFood: boolean
}

export default function Header({ onReset, hasFood }: Props) {
  return (
    <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
      <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="bg-green-500 text-white p-1.5 rounded-lg">
            <Salad size={20} />
          </div>
          <div>
            <h1 className="font-bold text-gray-900 leading-tight">NutriChat</h1>
            <p className="text-xs text-gray-500 leading-tight">AI nutrition analysis</p>
          </div>
        </div>
        {hasFood && (
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 hover:bg-gray-100 px-3 py-1.5 rounded-lg transition-colors"
          >
            <RotateCcw size={14} />
            New food
          </button>
        )}
      </div>
    </header>
  )
}

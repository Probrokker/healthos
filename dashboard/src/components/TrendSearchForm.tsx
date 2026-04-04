'use client'

import { useState, useTransition } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

export default function TrendSearchForm({ profileId }: { profileId: string }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [marker, setMarker] = useState(searchParams.get('marker') || '')
  const [isPending, startTransition] = useTransition()

  const suggestions = [
    'Гемоглобин', 'Лейкоциты', 'Тромбоциты', 'Эритроциты', 'СОЭ',
    'Глюкоза', 'Холестерин', 'Билирубин', 'АЛТ', 'АСТ',
    'Ферритин', 'Витамин D', 'ТТГ', 'Т4', 'ИФА',
    'Гематокрит', 'Нейтрофилы', 'Лимфоциты', 'Моноциты',
  ]

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!marker.trim()) return
    startTransition(() => {
      router.push(`/profile/${profileId}/trend?marker=${encodeURIComponent(marker.trim())}`)
    })
  }

  function handleSuggestion(s: string) {
    setMarker(s)
    startTransition(() => {
      router.push(`/profile/${profileId}/trend?marker=${encodeURIComponent(s)}`)
    })
  }

  return (
    <div className="mb-6">
      <form onSubmit={handleSubmit} className="flex gap-3">
        <div className="flex-1 relative">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
          <input
            type="text"
            value={marker}
            onChange={(e) => setMarker(e.target.value)}
            placeholder="Введите название маркера (напр. Гемоглобин)"
            className="w-full bg-bg-elevated/50 border border-bg-border rounded-xl px-4 py-2.5 pl-10 text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={isPending || !marker.trim()}
          className="px-5 py-2.5 bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors text-sm"
        >
          {isPending ? 'Поиск...' : 'Найти'}
        </button>
      </form>

      {/* Suggestions */}
      <div className="mt-3 flex flex-wrap gap-2">
        <span className="text-text-muted text-xs py-1">Популярные:</span>
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => handleSuggestion(s)}
            className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
              marker === s
                ? 'bg-accent/15 border-accent/40 text-accent'
                : 'bg-bg-elevated/50 border-bg-border text-text-secondary hover:text-text-primary hover:border-accent/30'
            }`}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

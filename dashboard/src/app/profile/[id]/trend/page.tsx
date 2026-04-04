import { Suspense } from 'react'
import { getLabTrend, formatDate, statusLabel, statusBadgeClass } from '@/lib/api'
import TrendChart from '@/components/TrendChart'
import TrendSearchForm from '@/components/TrendSearchForm'
import LoadingSpinner from '@/components/LoadingSpinner'

export default async function TrendPage({
  params,
  searchParams,
}: {
  params: { id: string }
  searchParams: { marker?: string }
}) {
  const { id } = params
  const marker = searchParams.marker || ''

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-text-primary font-semibold text-xl mb-1">Динамика маркера</h2>
        <p className="text-text-secondary text-sm">
          Выберите маркер для просмотра изменений во времени
        </p>
      </div>

      <Suspense fallback={null}>
        <TrendSearchForm profileId={id} />
      </Suspense>

      {marker ? (
        <Suspense fallback={<LoadingSpinner label="Загрузка данных..." />}>
          <TrendData profileId={id} marker={marker} />
        </Suspense>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4v16" stroke="#6366f1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <p className="text-text-secondary font-medium">Введите название маркера</p>
          <p className="text-text-muted text-sm mt-1">Например, «Гемоглобин» или «Глюкоза»</p>
        </div>
      )}
    </div>
  )
}

async function TrendData({ profileId, marker }: { profileId: string; marker: string }) {
  let data: Awaited<ReturnType<typeof getLabTrend>> = []
  let error = false

  try {
    data = await getLabTrend(profileId, marker)
  } catch {
    error = true
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-400">
        Не удалось загрузить данные для маркера «{marker}»
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12 text-text-secondary">
        Данные для маркера «{marker}» не найдены
      </div>
    )
  }

  // Summary stats
  const values = data.map((d) => d.value)
  const latest = data[data.length - 1]
  const oldest = data[0]
  const minVal = Math.min(...values)
  const maxVal = Math.max(...values)
  const avg = values.reduce((a, b) => a + b, 0) / values.length
  const unit = latest.unit

  const trend = latest.value > oldest.value ? '↑' : latest.value < oldest.value ? '↓' : '→'
  const trendColor =
    latest.status === 'normal'
      ? 'text-green-400'
      : latest.status.includes('critical')
      ? 'text-red-400'
      : 'text-yellow-400'

  return (
    <div>
      {/* Marker header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-text-primary font-bold text-lg">{marker}</h3>
        <div className="flex items-center gap-3">
          <span className={`text-xl font-bold ${trendColor}`}>{trend}</span>
          <span className={`text-sm px-3 py-1 rounded-full font-medium ${statusBadgeClass(latest.status)}`}>
            {statusLabel(latest.status)}
          </span>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Последнее', value: `${latest.value} ${unit}`, date: formatDate(latest.date) },
          { label: 'Минимум', value: `${minVal} ${unit}`, date: '' },
          { label: 'Максимум', value: `${maxVal} ${unit}`, date: '' },
          { label: 'Среднее', value: `${avg.toFixed(2)} ${unit}`, date: `${data.length} замеров` },
        ].map((s) => (
          <div key={s.label} className="bg-bg-elevated/40 rounded-xl p-3 border border-bg-border">
            <p className="text-text-muted text-xs uppercase tracking-wider mb-1">{s.label}</p>
            <p className="text-text-primary font-semibold">{s.value}</p>
            {s.date && <p className="text-text-muted text-xs mt-0.5">{s.date}</p>}
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="bg-bg-elevated/20 rounded-xl p-4 border border-bg-border">
        <TrendChart data={data} markerName={marker} />
      </div>

      {/* Data table */}
      <div className="mt-6">
        <h4 className="text-text-secondary text-sm font-medium mb-3">История замеров</h4>
        <div className="bg-bg-elevated/20 border border-bg-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-bg-border">
                <th className="text-left text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Дата</th>
                <th className="text-right text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Значение</th>
                <th className="text-right text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Норма</th>
                <th className="text-center text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Статус</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-bg-border">
              {[...data].reverse().map((point, i) => (
                <tr key={i} className="hover:bg-bg-elevated/30 transition-colors">
                  <td className="px-4 py-2.5 text-text-secondary">{formatDate(point.date)}</td>
                  <td className={`px-4 py-2.5 text-right font-mono font-semibold ${valueColor(point.status)}`}>
                    {point.value} {point.unit}
                  </td>
                  <td className="px-4 py-2.5 text-right text-text-muted font-mono text-xs">
                    {point.ref_min !== undefined && point.ref_max !== undefined
                      ? `${point.ref_min}–${point.ref_max}`
                      : '—'}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusBadgeClass(point.status)}`}>
                      {statusLabel(point.status)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function valueColor(status: string): string {
  switch (status) {
    case 'normal': return 'text-green-400'
    case 'low': return 'text-yellow-400'
    case 'high': return 'text-yellow-400'
    case 'critical': return 'text-red-400'
    case 'critical_low': return 'text-red-400'
    default: return 'text-text-primary'
  }
}

import Link from 'next/link'
import { getProfileLabs, formatDate, statusLabel, statusBadgeClass } from '@/lib/api'

export default async function LabsPage({ params }: { params: { id: string } }) {
  const { id } = params
  let labs: Awaited<ReturnType<typeof getProfileLabs>> = []
  let error = false

  try {
    labs = await getProfileLabs(id)
  } catch {
    error = true
  }

  // Group by date
  const grouped: Record<string, typeof labs> = {}
  for (const lab of labs) {
    const date = lab.date.split('T')[0]
    if (!grouped[date]) grouped[date] = []
    grouped[date].push(lab)
  }
  const sortedDates = Object.keys(grouped).sort((a, b) => b.localeCompare(a))

  const abnormalCount = labs.filter((l) => l.status !== 'normal').length

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-text-primary font-semibold text-xl">Анализы</h2>
          <p className="text-text-secondary text-sm mt-0.5">
            {labs.length} записей
            {abnormalCount > 0 && (
              <span className="ml-2 badge-critical text-xs px-2 py-0.5 rounded-full">
                {abnormalCount} отклонений
              </span>
            )}
          </p>
        </div>
        <Link
          href={`/profile/${id}/trend`}
          className="px-4 py-2 rounded-lg bg-accent/10 border border-accent/30 text-accent text-sm font-medium hover:bg-accent/20 transition-colors"
        >
          Динамика маркера →
        </Link>
      </div>

      {error && (
        <div className="text-center py-12 text-text-secondary">
          Не удалось загрузить анализы. Проверьте подключение к API.
        </div>
      )}

      {!error && labs.length === 0 && (
        <div className="text-center py-12 text-text-secondary">
          Анализы не найдены
        </div>
      )}

      {sortedDates.map((date) => (
        <div key={date} className="mb-8">
          {/* Date header */}
          <div className="flex items-center gap-3 mb-3">
            <div className="h-px flex-1 bg-bg-border" />
            <span className="text-text-muted text-xs font-medium px-2">{formatDate(date)}</span>
            <div className="h-px flex-1 bg-bg-border" />
          </div>

          {/* Lab results table */}
          <div className="bg-bg-elevated/30 border border-bg-border rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-bg-border">
                  <th className="text-left text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Маркер</th>
                  <th className="text-right text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Значение</th>
                  <th className="text-right text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Референс</th>
                  <th className="text-center text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Статус</th>
                  <th className="text-right text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-bg-border">
                {grouped[date].map((lab, idx) => {
                  const isAbnormal = lab.status !== 'normal'
                  return (
                    <tr
                      key={lab.id || idx}
                      className={`transition-colors ${
                        isAbnormal ? 'bg-red-500/3 hover:bg-red-500/6' : 'hover:bg-bg-elevated/50'
                      }`}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {isAbnormal && (
                            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                              lab.status.includes('critical') ? 'bg-red-400' : 'bg-yellow-400'
                            }`} />
                          )}
                          <span className={`font-medium text-sm ${isAbnormal ? 'text-text-primary' : 'text-text-secondary'}`}>
                            {lab.marker}
                          </span>
                          {lab.lab_type && (
                            <span className="text-text-muted text-xs">{lab.lab_type}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-semibold text-sm font-mono ${labStatusColor(lab.status)}`}>
                          {lab.value} {lab.unit}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-text-muted text-xs font-mono">
                          {lab.ref_min !== undefined && lab.ref_max !== undefined
                            ? `${lab.ref_min} – ${lab.ref_max}`
                            : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${statusBadgeClass(lab.status)}`}>
                          {statusLabel(lab.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/profile/${id}/trend?marker=${encodeURIComponent(lab.marker)}`}
                          className="text-text-muted hover:text-accent text-xs transition-colors"
                          title="Смотреть динамику"
                        >
                          Динамика →
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}

function labStatusColor(status: string): string {
  switch (status) {
    case 'normal': return 'text-green-400'
    case 'low': return 'text-yellow-400'
    case 'high': return 'text-yellow-400'
    case 'critical': return 'text-red-400'
    case 'critical_low': return 'text-red-400'
    default: return 'text-text-secondary'
  }
}

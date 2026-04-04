import { getGrowthRecords, formatDate } from '@/lib/api'
import GrowthChart from '@/components/GrowthChart'

export default async function GrowthPage({ params }: { params: { id: string } }) {
  const { id } = params
  let records: Awaited<ReturnType<typeof getGrowthRecords>> = []
  let error = false

  try {
    records = await getGrowthRecords(id)
  } catch {
    error = true
  }

  const latest = records.length > 0 ? records[records.length - 1] : null
  const oldest = records.length > 0 ? records[0] : null

  // Compute growth deltas
  const heightDelta =
    latest && oldest && latest !== oldest
      ? (latest.height_cm - oldest.height_cm).toFixed(1)
      : null
  const weightDelta =
    latest && oldest && latest !== oldest
      ? (latest.weight_kg - oldest.weight_kg).toFixed(1)
      : null

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-text-primary font-semibold text-xl">График роста</h2>
          <p className="text-text-secondary text-sm mt-0.5">
            {records.length > 0
              ? `${records.length} замеров с ${formatDate(records[0].date)}`
              : 'Данные о росте'}
          </p>
        </div>
      </div>

      {error && (
        <div className="text-center py-12 text-text-secondary">
          Не удалось загрузить данные роста. Проверьте подключение к API.
        </div>
      )}

      {!error && records.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-14 h-14 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center mb-4">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" stroke="#6366f1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <p className="text-text-secondary font-medium">Данные о росте отсутствуют</p>
          <p className="text-text-muted text-sm mt-1">Добавьте первый замер роста и веса</p>
        </div>
      )}

      {records.length > 0 && (
        <>
          {/* Current stats */}
          {latest && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              <div className="bg-bg-elevated/40 rounded-xl p-4 border border-bg-border">
                <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Рост</p>
                <p className="text-accent font-bold text-2xl">{latest.height_cm}</p>
                <p className="text-text-muted text-xs">см</p>
                {heightDelta && (
                  <p className={`text-xs mt-1 font-medium ${parseFloat(heightDelta) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {parseFloat(heightDelta) >= 0 ? '+' : ''}{heightDelta} см за период
                  </p>
                )}
              </div>
              <div className="bg-bg-elevated/40 rounded-xl p-4 border border-bg-border">
                <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Вес</p>
                <p className="text-green-400 font-bold text-2xl">{latest.weight_kg}</p>
                <p className="text-text-muted text-xs">кг</p>
                {weightDelta && (
                  <p className={`text-xs mt-1 font-medium ${parseFloat(weightDelta) >= 0 ? 'text-yellow-400' : 'text-green-400'}`}>
                    {parseFloat(weightDelta) >= 0 ? '+' : ''}{weightDelta} кг за период
                  </p>
                )}
              </div>
              <div className="bg-bg-elevated/40 rounded-xl p-4 border border-bg-border">
                <p className="text-text-muted text-xs uppercase tracking-wider mb-1">ИМТ</p>
                <p className={`font-bold text-2xl ${bmiColor(latest.bmi)}`}>
                  {latest.bmi !== undefined ? latest.bmi.toFixed(1) : '—'}
                </p>
                <p className="text-text-muted text-xs">{bmiLabel(latest.bmi)}</p>
              </div>
              <div className="bg-bg-elevated/40 rounded-xl p-4 border border-bg-border">
                <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Последний замер</p>
                <p className="text-text-primary font-semibold text-sm">{formatDate(latest.date)}</p>
                {latest.height_percentile !== undefined && (
                  <p className="text-text-muted text-xs mt-1">
                    Рост: {latest.height_percentile}й перцентиль
                  </p>
                )}
                {latest.weight_percentile !== undefined && (
                  <p className="text-text-muted text-xs">
                    Вес: {latest.weight_percentile}й перцентиль
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Chart */}
          <div className="bg-bg-elevated/20 rounded-xl p-4 border border-bg-border mb-6">
            <GrowthChart data={records} />
          </div>

          {/* Data table */}
          <div>
            <h4 className="text-text-secondary text-sm font-medium mb-3">История замеров</h4>
            <div className="bg-bg-elevated/20 border border-bg-border rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-bg-border">
                    <th className="text-left text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Дата</th>
                    <th className="text-right text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Рост, см</th>
                    <th className="text-right text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Вес, кг</th>
                    <th className="text-right text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">ИМТ</th>
                    <th className="text-right text-text-muted text-xs uppercase tracking-wider px-4 py-3 font-medium">Перцентили</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-bg-border">
                  {[...records].reverse().map((rec, i) => (
                    <tr key={i} className="hover:bg-bg-elevated/30 transition-colors">
                      <td className="px-4 py-2.5 text-text-secondary">{formatDate(rec.date)}</td>
                      <td className="px-4 py-2.5 text-right text-accent font-mono font-semibold">
                        {rec.height_cm}
                      </td>
                      <td className="px-4 py-2.5 text-right text-green-400 font-mono font-semibold">
                        {rec.weight_kg}
                      </td>
                      <td className={`px-4 py-2.5 text-right font-mono font-semibold ${bmiColor(rec.bmi)}`}>
                        {rec.bmi !== undefined ? rec.bmi.toFixed(1) : '—'}
                      </td>
                      <td className="px-4 py-2.5 text-right text-text-muted text-xs">
                        {rec.height_percentile !== undefined || rec.weight_percentile !== undefined
                          ? `Р: ${rec.height_percentile ?? '—'} / В: ${rec.weight_percentile ?? '—'}`
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function bmiColor(bmi?: number): string {
  if (bmi === undefined) return 'text-text-primary'
  if (bmi < 16) return 'text-red-400'
  if (bmi < 18.5) return 'text-yellow-400'
  if (bmi <= 24.9) return 'text-green-400'
  if (bmi <= 29.9) return 'text-yellow-400'
  return 'text-red-400'
}

function bmiLabel(bmi?: number): string {
  if (bmi === undefined) return ''
  if (bmi < 16) return 'Выраженный дефицит'
  if (bmi < 18.5) return 'Дефицит веса'
  if (bmi <= 24.9) return 'Норма'
  if (bmi <= 29.9) return 'Избыточный вес'
  return 'Ожирение'
}

import Link from 'next/link'
import { getProfileStats, getVisits, getMedications, formatDate, statusBadgeClass, statusLabel } from '@/lib/api'
import StatCard from '@/components/StatCard'

export default async function ProfileOverviewPage({ params }: { params: { id: string } }) {
  const { id } = params

  let stats: { labs_count: number; visits_count: number; active_medications: number; last_lab_date?: string; last_lab_type?: string; recent_abnormal_markers: string[] } = { labs_count: 0, visits_count: 0, active_medications: 0, last_lab_date: undefined, last_lab_type: undefined, recent_abnormal_markers: [] }
  let recentVisits: Awaited<ReturnType<typeof getVisits>> = []
  let activeMeds: Awaited<ReturnType<typeof getMedications>> = []

  try {
    stats = await getProfileStats(id)
  } catch {}

  try {
    const visits = await getVisits(id)
    recentVisits = visits.slice(0, 3)
  } catch {}

  try {
    activeMeds = await getMedications(id, true)
  } catch {}

  return (
    <div className="space-y-6">
      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Анализов"
          value={stats.labs_count}
          accent
        />
        <StatCard
          label="Визитов"
          value={stats.visits_count}
        />
        <StatCard
          label="Лекарств (акт.)"
          value={stats.active_medications}
          warning={stats.active_medications > 0}
        />
        <StatCard
          label="Отклонений"
          value={stats.recent_abnormal_markers.length}
          danger={stats.recent_abnormal_markers.length > 0}
          sub={stats.last_lab_date ? `Посл. анализ: ${formatDate(stats.last_lab_date)}` : undefined}
        />
      </div>

      {/* Abnormal markers alert */}
      {stats.recent_abnormal_markers.length > 0 && (
        <div className="bg-red-500/8 border border-red-500/20 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-red-500/15 flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-red-400 font-semibold text-sm mb-2">Требуют внимания</h3>
              <div className="flex flex-wrap gap-2">
                {stats.recent_abnormal_markers.map((m) => (
                  <span key={m} className="badge-critical text-xs px-2.5 py-1 rounded-full">
                    {m}
                  </span>
                ))}
              </div>
            </div>
            <Link
              href={`/profile/${id}/labs`}
              className="text-accent text-sm hover:underline flex-shrink-0"
            >
              Все анализы →
            </Link>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recent visits */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-text-primary font-semibold">Последние визиты</h3>
          </div>
          {recentVisits.length === 0 ? (
            <p className="text-text-muted text-sm py-4">Нет данных о визитах</p>
          ) : (
            <div className="space-y-3">
              {recentVisits.map((visit) => (
                <div key={visit.id} className="bg-bg-elevated/40 rounded-lg p-3 border border-bg-border">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-text-primary text-sm font-medium">{visit.doctor_name}</p>
                      {visit.specialty && (
                        <p className="text-text-muted text-xs">{visit.specialty}</p>
                      )}
                      {visit.diagnosis && (
                        <p className="text-text-secondary text-xs mt-1">{visit.diagnosis}</p>
                      )}
                    </div>
                    <span className="text-text-muted text-xs whitespace-nowrap">{formatDate(visit.date)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Active medications */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-text-primary font-semibold">Активные лекарства</h3>
          </div>
          {activeMeds.length === 0 ? (
            <p className="text-text-muted text-sm py-4">Нет активных назначений</p>
          ) : (
            <div className="space-y-3">
              {activeMeds.map((med) => (
                <div key={med.id} className="bg-bg-elevated/40 rounded-lg p-3 border border-bg-border">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-text-primary text-sm font-medium">{med.name}</p>
                      <p className="text-text-muted text-xs">{med.dosage} · {med.frequency}</p>
                      {med.prescribed_by && (
                        <p className="text-text-muted text-xs mt-0.5">Назначил: {med.prescribed_by}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <span className="badge-normal text-xs px-2 py-0.5 rounded-full">Активно</span>
                      <p className="text-text-muted text-xs mt-1">{formatDate(med.start_date)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-bg-border">
        {[
          { href: `/profile/${id}/labs`, label: 'Все анализы', icon: '🔬' },
          { href: `/profile/${id}/trend`, label: 'Динамика маркера', icon: '📈' },
          { href: `/profile/${id}/growth`, label: 'График роста', icon: '📏' },
        ].map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="bg-accent/8 hover:bg-accent/15 border border-accent/20 rounded-lg p-3 text-center transition-colors"
          >
            <span className="block text-lg mb-1">{link.icon}</span>
            <span className="text-accent text-sm font-medium">{link.label}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}

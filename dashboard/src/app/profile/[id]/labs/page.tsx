import Link from "next/link"
import { getProfileLabs, formatDate, statusLabel, statusBadgeClass } from "@/lib/api"

interface Marker {
  name: string
  value: string
  unit?: string
  status?: string
  ref_min?: string
  ref_max?: string
}

function markerStatusColor(status?: string): string {
  if (!status || status === "normal") return "text-green-400"
  if (["low","high"].includes(status)) return "text-yellow-400"
  if (status.includes("critical")) return "text-red-400"
  return "text-text-secondary"
}

export default async function LabsPage({ params }: { params: { id: string } }) {
  const { id } = params
  let labs: Awaited<ReturnType<typeof getProfileLabs>> = []
  let error = false

  try {
    labs = await getProfileLabs(id)
  } catch {
    error = true
  }

  // Считаем аномальные маркеры
  const abnormalCount = labs.reduce((sum, lab) => {
    const markers: Marker[] = lab.markers || []
    return sum + markers.filter((m) => m.status && m.status !== "normal").length
  }, 0)

  // Сортируем по дате убыванию
  const sorted = [...labs].sort((a, b) => b.date.localeCompare(a.date))

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-semibold text-xl" style={{ color: "var(--text-primary)" }}>Анализы</h2>
          <p className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>
            {labs.length} записей
            {abnormalCount > 0 && (
              <span className="ml-2 badge-critical text-xs px-2 py-0.5 rounded-full">
                {abnormalCount} откл.
              </span>
            )}
          </p>
        </div>
        <Link
          href={`/profile/${id}/trend`}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{ backgroundColor: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.3)", color: "var(--accent)" }}
        >
          Динамика маркера →
        </Link>
      </div>

      {error && (
        <div className="text-center py-12" style={{ color: "var(--text-secondary)" }}>
          Не удалось загрузить анализы.
        </div>
      )}

      {!error && labs.length === 0 && (
        <div className="text-center py-12" style={{ color: "var(--text-secondary)" }}>
          Анализов пока нет. Отправьте фото бланка боту — он всё распознает.
        </div>
      )}

      <div className="space-y-6">
        {sorted.map((lab) => {
          const markers: Marker[] = lab.markers || []
          const abnormal = markers.filter((m) => m.status && m.status !== "normal")

          return (
            <div key={lab.id} className="rounded-xl overflow-hidden"
                 style={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--bg-border)" }}>
              {/* Заголовок анализа */}
              <div className="px-5 py-4 flex items-center justify-between"
                   style={{ borderBottom: "1px solid var(--bg-border)" }}>
                <div>
                  <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
                    {lab.test_type || "Анализ"}
                  </span>
                  {lab.lab_name && (
                    <span className="ml-2 text-sm" style={{ color: "var(--text-muted)" }}>
                      {lab.lab_name}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {abnormal.length > 0 && (
                    <span className="badge-critical text-xs px-2 py-0.5 rounded-full">
                      {abnormal.length} откл.
                    </span>
                  )}
                  <span className="text-sm" style={{ color: "var(--text-muted)" }}>
                    {formatDate(lab.date)}
                  </span>
                </div>
              </div>

              {/* Маркеры */}
              {markers.length > 0 ? (
                <table className="w-full">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--bg-border)" }}>
                      <th className="text-left text-xs uppercase tracking-wider px-5 py-2.5 font-medium" style={{ color: "var(--text-muted)" }}>Показатель</th>
                      <th className="text-right text-xs uppercase tracking-wider px-5 py-2.5 font-medium" style={{ color: "var(--text-muted)" }}>Значение</th>
                      <th className="text-right text-xs uppercase tracking-wider px-5 py-2.5 font-medium" style={{ color: "var(--text-muted)" }}>Норма</th>
                      <th className="text-center text-xs uppercase tracking-wider px-5 py-2.5 font-medium" style={{ color: "var(--text-muted)" }}>Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {markers.map((m, idx) => {
                      const isAbnormal = m.status && m.status !== "normal"
                      return (
                        <tr key={idx}
                            style={{ borderTop: idx > 0 ? "1px solid var(--bg-border)" : "none",
                                     backgroundColor: isAbnormal ? "rgba(239,68,68,0.03)" : "transparent" }}>
                          <td className="px-5 py-3">
                            <div className="flex items-center gap-2">
                              {isAbnormal && (
                                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                                  m.status?.includes("critical") ? "bg-red-400" : "bg-yellow-400"
                                }`} />
                              )}
                              <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                                {m.name}
                              </span>
                            </div>
                          </td>
                          <td className="px-5 py-3 text-right">
                            <span className={`font-semibold text-sm font-mono ${markerStatusColor(m.status)}`}>
                              {m.value} {m.unit || ""}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-right">
                            <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>
                              {m.ref_min && m.ref_max ? `${m.ref_min} – ${m.ref_max}` : "—"}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-center">
                            <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${statusBadgeClass(m.status || "normal")}`}>
                              {statusLabel(m.status || "normal")}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              ) : (
                <div className="px-5 py-4 text-sm" style={{ color: "var(--text-muted)" }}>
                  Маркеры не извлечены
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}


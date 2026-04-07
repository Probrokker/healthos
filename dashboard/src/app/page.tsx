import Link from "next/link"
import { formatDate } from "@/lib/api"
import Avatar from "@/components/Avatar"

interface FamilyMember {
  id: number
  name: string
  is_child: boolean
  age_years: number
  age_months: number
  labs_count: number
  active_medications: number
  last_visit_date?: string
  last_visit_specialty?: string
}

function ageLabel(age: number): string {
  const mod10 = age % 10
  const mod100 = age % 100
  if (mod100 >= 11 && mod100 <= 14) return "лет"
  if (mod10 === 1) return "год"
  if (mod10 >= 2 && mod10 <= 4) return "года"
  return "лет"
}

function ageStr(m: FamilyMember): string {
  if (m.age_years === 0) {
    if (m.age_months === 0) return "Новорождённый"
    return `${m.age_months} мес.`
  }
  return `${m.age_years} ${ageLabel(m.age_years)}`
}

function MemberCard({ m }: { m: FamilyMember }) {
  return (
    <Link
      href={`/profile/${m.id}`}
      className="rounded-xl p-5 card-hover block border"
      style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--bg-border)" }}
    >
      <div className="flex items-center gap-4 mb-5">
        <Avatar profileId={String(m.id)} name={m.name} size="lg" />
        <div>
          <h2 className="font-semibold text-lg" style={{ color: "var(--text-primary)" }}>{m.name}</h2>
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{ageStr(m)}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="rounded-lg p-3" style={{ backgroundColor: "var(--bg-elevated)" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Анализы</p>
          <p className="font-semibold text-lg" style={{ color: "var(--text-primary)" }}>{m.labs_count}</p>
        </div>
        <div className="rounded-lg p-3" style={{ backgroundColor: "var(--bg-elevated)" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Последний визит</p>
          <p className="font-medium text-sm" style={{ color: "var(--text-primary)" }}>
            {m.last_visit_date ? formatDate(m.last_visit_date) : "—"}
          </p>
        </div>
        <div className="rounded-lg p-3" style={{ backgroundColor: "var(--bg-elevated)" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Лекарства</p>
          <p className={`font-semibold text-lg ${m.active_medications > 0 ? "text-yellow-400" : ""}`}
             style={m.active_medications === 0 ? { color: "var(--text-primary)" } : {}}>
            {m.active_medications}
          </p>
        </div>
        <div className="rounded-lg p-3" style={{ backgroundColor: "var(--bg-elevated)" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Специальность</p>
          <p className="font-medium text-sm" style={{ color: "var(--text-primary)" }}>
            {m.last_visit_specialty || "—"}
          </p>
        </div>
      </div>

      <div className="flex justify-end">
        <span className="text-sm font-medium" style={{ color: "var(--accent)" }}>Открыть →</span>
      </div>
    </Link>
  )
}

function SectionLabel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--text-secondary)" }}>
        {label}
      </span>
      <div className="flex-1 h-px" style={{ backgroundColor: "var(--bg-border)" }} />
    </div>
  )
}

async function getFamilyData(): Promise<FamilyMember[]> {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/family/overview`,
      { cache: "no-store" }
    )
    if (!res.ok) throw new Error("API error")
    const data = await res.json()
    return data.family || []
  } catch {
    return []
  }
}

export default async function FamilyOverviewPage() {
  const members = await getFamilyData()

  const parents = members.filter((m) => !m.is_child)
  const children = members.filter((m) => m.is_child)

  const totalLabs = members.reduce((s, m) => s + (m.labs_count || 0), 0)
  const totalMeds = members.reduce((s, m) => s + (m.active_medications || 0), 0)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>Обзор семьи</h1>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Мониторинг здоровья всех членов семьи</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-8">
        <div className="rounded-xl p-4 border" style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--bg-border)" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Всего анализов</p>
          <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>{totalLabs}</p>
        </div>
        <div className="rounded-xl p-4 border" style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--bg-border)" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Активных лекарств</p>
          <p className={`text-2xl font-bold ${totalMeds > 0 ? "text-yellow-400" : ""}`}
             style={totalMeds === 0 ? { color: "var(--text-primary)" } : {}}>{totalMeds}</p>
        </div>
        <div className="rounded-xl p-4 border col-span-2 sm:col-span-1" style={{ backgroundColor: "var(--bg-card)", borderColor: "var(--bg-border)" }}>
          <p className="text-xs uppercase tracking-wider mb-1" style={{ color: "var(--text-muted)" }}>Членов семьи</p>
          <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>{members.length}</p>
        </div>
      </div>

      {/* Родители */}
      {parents.length > 0 && (
        <div className="mb-8">
          <SectionLabel label="Родители" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {parents.map((m) => <MemberCard key={m.id} m={m} />)}
          </div>
        </div>
      )}

      {/* Дети */}
      {children.length > 0 && (
        <div>
          <SectionLabel label="Дети" />
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {children.map((m) => <MemberCard key={m.id} m={m} />)}
          </div>
        </div>
      )}

      {members.length === 0 && (
        <div className="text-center py-20" style={{ color: "var(--text-secondary)" }}>
          Не удалось загрузить данные. Проверьте подключение к API.
        </div>
      )}
    </div>
  )
}

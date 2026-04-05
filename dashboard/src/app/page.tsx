import Link from "next/link"
import { getFamilyOverview, getProfiles, getProfileStats, calcAge, formatDate } from "@/lib/api"
import Avatar from "@/components/Avatar"

function StatusDot({ count, label }: { count: number; label: string }) {
  if (count === 0) return null
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs badge-critical animate-pulse-red">
      <span className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
      {count} {label}
    </span>
  )
}

interface MemberCardData {
  id: string
  name: string
  birth_date: string
  is_child: boolean
  age: number
  labs_count: number
  visits_count: number
  active_medications: number
  last_lab_date?: string
  last_lab_type?: string
  recent_abnormal_markers: string[]
}

async function getMemberData(profile: { id: string; name: string; birth_date: string; is_child?: boolean }): Promise<MemberCardData> {
  try {
    const stats = await getProfileStats(profile.id)
    return {
      ...profile,
      is_child: profile.is_child ?? false,
      age: calcAge(profile.birth_date),
      labs_count: stats.labs_count,
      visits_count: stats.visits_count,
      active_medications: stats.active_medications,
      last_lab_date: stats.last_lab_date,
      last_lab_type: stats.last_lab_type,
      recent_abnormal_markers: Array.isArray(stats.recent_abnormal_markers) ? stats.recent_abnormal_markers : [],
    }
  } catch {
    return {
      ...profile,
      is_child: profile.is_child ?? false,
      age: calcAge(profile.birth_date),
      labs_count: 0,
      visits_count: 0,
      active_medications: 0,
      recent_abnormal_markers: [],
    }
  }
}

function MemberCard({ member }: { member: MemberCardData }) {
  return (
    <Link
      href={`/profile/${member.id}`}
      className="bg-bg-card border border-bg-border rounded-xl p-6 card-hover block"
    >
      <div className="flex items-center gap-4 mb-5">
        <Avatar profileId={member.id} name={member.name} size="lg" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-text-primary font-semibold text-lg">{member.name}</h2>
            {member.recent_abnormal_markers.length > 0 && (
              <StatusDot count={member.recent_abnormal_markers.length} label="откл." />
            )}
          </div>
          <p className="text-text-secondary text-sm">
            {member.age < 1 ? "До 1 года" : member.age === 1 ? "1 год" : `${member.age} ${ageLabel(member.age)}`}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-bg-elevated/40 rounded-lg p-3">
          <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Анализы</p>
          <p className="text-text-primary font-semibold text-lg">{member.labs_count}</p>
        </div>
        <div className="bg-bg-elevated/40 rounded-lg p-3">
          <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Визиты</p>
          <p className="text-text-primary font-semibold text-lg">{member.visits_count}</p>
        </div>
        <div className="bg-bg-elevated/40 rounded-lg p-3">
          <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Лекарства</p>
          <p className={`font-semibold text-lg ${member.active_medications > 0 ? "text-yellow-400" : "text-text-primary"}`}>
            {member.active_medications}
          </p>
        </div>
        <div className="bg-bg-elevated/40 rounded-lg p-3">
          <p className="text-text-muted text-xs uppercase tracking-wider mb-1">Последний анализ</p>
          <p className="text-text-primary font-medium text-sm">
            {member.last_lab_date ? formatDate(member.last_lab_date) : "—"}
          </p>
        </div>
      </div>

      {member.recent_abnormal_markers.length > 0 && (
        <div className="border-t border-bg-border pt-3">
          <p className="text-text-muted text-xs uppercase tracking-wider mb-2">Отклонения</p>
          <div className="flex flex-wrap gap-1.5">
            {member.recent_abnormal_markers.slice(0, 4).map((marker) => (
              <span key={marker} className="badge-critical text-xs px-2 py-0.5 rounded-full">{marker}</span>
            ))}
            {member.recent_abnormal_markers.length > 4 && (
              <span className="text-text-muted text-xs px-2 py-0.5">+{member.recent_abnormal_markers.length - 4}</span>
            )}
          </div>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between">
        {member.last_lab_type && <span className="text-text-muted text-xs">{member.last_lab_type}</span>}
        <span className="ml-auto text-accent text-sm font-medium">Открыть →</span>
      </div>
    </Link>
  )
}

function SectionLabel({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="text-text-secondary text-xs font-semibold uppercase tracking-widest">{label}</span>
      <div className="flex-1 h-px" style={{ backgroundColor: "var(--bg-border)" }} />
    </div>
  )
}

export default async function FamilyOverviewPage() {
  let profiles: { id: string; name: string; birth_date: string; is_child?: boolean }[] = []

  try {
    try {
      const overview = await getFamilyOverview()
      if (overview.members) {
        profiles = overview.members.map((m: { id: string; name: string; birth_date: string; is_child?: boolean }) => ({
          id: m.id,
          name: m.name,
          birth_date: m.birth_date,
          is_child: m.is_child,
        }))
      }
    } catch {
      const raw = await getProfiles()
      profiles = raw.map((p: { id: string; name: string; birthdate?: string; birth_date?: string; is_child?: boolean }) => ({
        id: p.id,
        name: p.name,
        birth_date: p.birthdate || p.birth_date || "",
        is_child: p.is_child,
      }))
    }
  } catch {
    profiles = [
      { id: "1", name: "Кирилл", birth_date: "1989-09-14", is_child: false },
      { id: "7", name: "Маша",   birth_date: "1987-01-21", is_child: false },
      { id: "2", name: "София",  birth_date: "2015-11-28", is_child: true },
      { id: "3", name: "Аня",    birth_date: "2019-03-04", is_child: true },
      { id: "4", name: "Лука",   birth_date: "2023-04-06", is_child: true },
      { id: "5", name: "Федор",  birth_date: "2025-09-12", is_child: true },
    ]
  }

  const members = await Promise.all(profiles.map(getMemberData))

  const parents = members.filter((m) => !m.is_child)
  const children = members.filter((m) => m.is_child)

  const totalAbnormal = members.reduce((s, m) => s + (Array.isArray(m.recent_abnormal_markers) ? m.recent_abnormal_markers.length : 0), 0)
  const totalMeds = members.reduce((s, m) => s + m.active_medications, 0)
  const totalLabs = members.reduce((s, m) => s + m.labs_count, 0)

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary mb-2">Семейный обзор</h1>
        <p className="text-text-secondary">Мониторинг здоровья всех членов семьи</p>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-2 mb-8 overflow-hidden">
        <div className="bg-bg-card border border-bg-border rounded-xl p-3 flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-4">
          <div className="w-10 h-10 rounded-lg bg-accent/15 flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" stroke="#6366f1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <p className="text-text-muted text-xs uppercase tracking-wider">Всего анализов</p>
            <p className="text-2xl font-bold text-text-primary">{totalLabs}</p>
          </div>
        </div>
        <div className="bg-bg-card border border-bg-border rounded-xl p-3 flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-4">
          <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <p className="text-text-muted text-xs uppercase tracking-wider">Активных лекарств</p>
            <p className="text-2xl font-bold text-text-primary">{totalMeds}</p>
          </div>
        </div>
        <div className={`bg-bg-card border rounded-xl p-4 flex items-center gap-4 ${totalAbnormal > 0 ? "border-red-500/30" : "border-bg-border"}`}>
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${totalAbnormal > 0 ? "bg-red-500/10" : "bg-bg-elevated"}`}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke={totalAbnormal > 0 ? "#ef4444" : "#8b8fa8"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <p className="text-text-muted text-xs uppercase tracking-wider">Отклонений</p>
            <p className={`text-2xl font-bold ${totalAbnormal > 0 ? "text-red-400" : "text-text-primary"}`}>{totalAbnormal}</p>
          </div>
        </div>
      </div>

      {/* Родители */}
      {parents.length > 0 && (
        <div className="mb-8">
          <SectionLabel label="Родители" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {parents.map((m) => <MemberCard key={m.id} member={m} />)}
          </div>
        </div>
      )}

      {/* Дети */}
      {children.length > 0 && (
        <div>
          <SectionLabel label="Дети" />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {children.map((m) => <MemberCard key={m.id} member={m} />)}
          </div>
        </div>
      )}
    </div>
  )
}

function ageLabel(age: number): string {
  if ([1,21,31,41,51,61].includes(age)) return "год"
  if ([2,3,4,22,23,24,32,33,34].includes(age)) return "года"
  return "лет"
}

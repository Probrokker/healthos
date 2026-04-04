const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" })
  if (!res.ok) throw new Error(`API error ${res.status} for ${path}`)
  return res.json()
}

export interface RawProfile {
  id: number
  name: string
  birthdate: string
  gender?: string
  blood_type?: string
  is_child: boolean
  age_years: number
  age_months: number
  allergies?: string[]
  chronic_conditions?: string[]
}

export interface NormalizedProfile {
  id: string
  name: string
  birth_date: string
  is_child: boolean
  age: number
}

export interface ProfileStats {
  labs_count: number
  visits_count: number
  active_medications: number
  last_lab_date?: string
  last_lab_type?: string
  recent_abnormal_markers: string[]
}

export interface TrendPoint {
  date: string
  value: number
  unit: string
  status: string
  ref_min?: number
  ref_max?: number
}

export interface Visit {
  id: string
  date: string
  doctor_name?: string
  specialty?: string
  diagnosis?: string
  recommendations?: string
}

export interface GrowthRecord {
  date: string
  height_cm: number
  weight_kg: number
  bmi?: number
  height_percentile?: number
  weight_percentile?: number
}

export interface LabResult {
  id: string
  date: string
  test_type?: string
  lab_name?: string
  markers?: Array<{
    name: string
    value: string
    unit?: string
    status?: string
    ref_min?: string
    ref_max?: string
  }>
}

export interface Medication {
  id: string
  name: string
  dosage?: string
  frequency?: string
  start_date?: string
  end_date?: string
  is_active: boolean
  reason?: string
}

// Нормализуем профиль из формата API в формат дашборда
function normalizeProfile(p: RawProfile): NormalizedProfile {
  return {
    id: String(p.id),
    name: p.name,
    birth_date: p.birthdate,
    is_child: p.is_child,
    age: p.age_years,
  }
}

// Получить все профили
export async function getProfiles(): Promise<NormalizedProfile[]> {
  const raw = await apiFetch<RawProfile[]>("/profiles")
  return raw.map(normalizeProfile)
}

// Получить семейный обзор — используем /profiles + /stats
export async function getFamilyOverview(): Promise<{ members: NormalizedProfile[] }> {
  const raw = await apiFetch<{ family: RawProfile[] }>("/family/overview")
  return { members: raw.family.map(normalizeProfile) }
}

export async function getProfile(id: string): Promise<NormalizedProfile> {
  const raw = await apiFetch<RawProfile>(`/profiles/${id}`)
  return normalizeProfile(raw)
}

export async function getProfileStats(id: string): Promise<ProfileStats> {
  return apiFetch<ProfileStats>(`/profiles/${id}/stats`)
}

export async function getProfileLabs(id: string): Promise<LabResult[]> {
  return apiFetch<LabResult[]>(`/profiles/${id}/labs`)
}

export async function getLabTrend(id: string, marker: string): Promise<TrendPoint[]> {
  return apiFetch<TrendPoint[]>(`/profiles/${id}/labs/trend?marker=${encodeURIComponent(marker)}`)
}

export async function getVisits(id: string): Promise<Visit[]> {
  return apiFetch<Visit[]>(`/profiles/${id}/visits`)
}

export async function getGrowthRecords(id: string): Promise<GrowthRecord[]> {
  return apiFetch<GrowthRecord[]>(`/profiles/${id}/growth`)
}

export async function getMedications(id: string, activeOnly = false): Promise<Medication[]> {
  return apiFetch<Medication[]>(`/profiles/${id}/medications${activeOnly ? "?active_only=true" : ""}`)
}

// Helpers
export function calcAge(birthDate: string): number {
  if (!birthDate) return 0
  const birth = new Date(birthDate)
  const now = new Date()
  let age = now.getFullYear() - birth.getFullYear()
  const m = now.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age--
  return age
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return "—"
  return new Date(dateStr).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" })
}

export function formatDateShort(dateStr: string): string {
  if (!dateStr) return "—"
  return new Date(dateStr).toLocaleDateString("ru-RU", { day: "2-digit", month: "short", year: "numeric" })
}

export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    normal: "Норма", low: "Понижен", high: "Повышен",
    critical: "Критично", critical_low: "Крит. низкий", critical_high: "Крит. высокий"
  }
  return map[status] || status
}

export function statusColor(status: string): string {
  if (status === "normal") return "text-green-400"
  if (["low","high"].includes(status)) return "text-yellow-400"
  if (status.includes("critical")) return "text-red-400"
  return "text-text-secondary"
}

export function statusBadgeClass(status: string): string {
  if (status === "normal") return "badge-normal"
  if (["low","high"].includes(status)) return "badge-warning"
  if (status.includes("critical")) return "badge-critical"
  return ""
}


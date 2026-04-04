const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText} for ${path}`)
  }
  return res.json()
}

// Types
export interface Profile {
  id: string
  name: string
  birth_date: string
  gender?: string
  avatar?: string
}

export interface FamilyMember extends Profile {
  age: number
  labs_count: number
  last_visit?: string
  active_medications: number
  abnormal_markers_count: number
  last_lab_date?: string
}

export interface FamilyOverview {
  members: FamilyMember[]
}

export interface LabResult {
  id: string
  date: string
  marker: string
  value: number
  unit: string
  status: 'normal' | 'low' | 'high' | 'critical' | 'critical_low'
  ref_min?: number
  ref_max?: number
  lab_type?: string
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
  doctor: string
  specialty?: string
  notes?: string
  diagnosis?: string
}

export interface GrowthRecord {
  date: string
  height_cm: number
  weight_kg: number
  bmi?: number
  height_percentile?: number
  weight_percentile?: number
}

export interface Medication {
  id: string
  name: string
  dosage: string
  frequency: string
  start_date: string
  end_date?: string
  active: boolean
  prescribed_by?: string
}

export interface ProfileStats {
  labs_count: number
  visits_count: number
  active_medications: number
  last_lab_date?: string
  last_lab_type?: string
  recent_abnormal_markers: string[]
}

// API functions
export async function getFamilyOverview(): Promise<FamilyOverview> {
  return apiFetch<FamilyOverview>('/family/overview')
}

export async function getProfiles(): Promise<Profile[]> {
  return apiFetch<Profile[]>('/profiles')
}

export async function getProfile(id: string): Promise<Profile> {
  return apiFetch<Profile>(`/profiles/${id}`)
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
  return apiFetch<Medication[]>(`/profiles/${id}/medications${activeOnly ? '?active_only=true' : ''}`)
}

export async function getProfileStats(id: string): Promise<ProfileStats> {
  return apiFetch<ProfileStats>(`/profiles/${id}/stats`)
}

// Helpers
export function calcAge(birthDate: string): number {
  const birth = new Date(birthDate)
  const now = new Date()
  let age = now.getFullYear() - birth.getFullYear()
  const m = now.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) age--
  return age
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function formatDateShort(dateStr: string): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function statusLabel(status: string): string {
  switch (status) {
    case 'normal': return 'Норма'
    case 'low': return 'Понижен'
    case 'high': return 'Повышен'
    case 'critical': return 'Критично'
    case 'critical_low': return 'Крит. низкий'
    default: return status
  }
}

export function statusColor(status: string): string {
  switch (status) {
    case 'normal': return 'text-green-400'
    case 'low': return 'text-yellow-400'
    case 'high': return 'text-yellow-400'
    case 'critical': return 'text-red-400'
    case 'critical_low': return 'text-red-400'
    default: return 'text-text-secondary'
  }
}

export function statusBadgeClass(status: string): string {
  switch (status) {
    case 'normal': return 'badge-normal'
    case 'low': return 'badge-warning'
    case 'high': return 'badge-warning'
    case 'critical': return 'badge-critical'
    case 'critical_low': return 'badge-critical'
    default: return ''
  }
}

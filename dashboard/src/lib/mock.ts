/**
 * Mock data for development / when API is unavailable
 * Used by components that show placeholder states
 */

export const MOCK_PROFILES = [
  { id: '1', name: 'Кирилл', birth_date: '1989-09-14' },
  { id: '2', name: 'София', birth_date: '2015-11-28' },
  { id: '3', name: 'Аня', birth_date: '2019-03-04' },
  { id: '4', name: 'Лука', birth_date: '2023-04-06' },
  { id: '5', name: 'Федор', birth_date: '2025-09-12' },
]

export const PROFILE_INITIALS: Record<string, string> = {
  '1': 'КИ',
  '2': 'СО',
  '3': 'АН',
  '4': 'ЛУ',
  '5': 'ФЕ',
}

export const AVATAR_COLORS: Record<string, string> = {
  '1': '#6366f1',
  '2': '#ec4899',
  '3': '#f59e0b',
  '4': '#22c55e',
  '5': '#06b6d4',
}

import { getProfile, calcAge } from '@/lib/api'
import Avatar from '@/components/Avatar'
import ProfileTabs from '@/components/ProfileTabs'

export default async function ProfileLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { id: string }
}) {
  let profile = { id: params.id, name: '—', birth_date: '' }
  let age = 0

  try {
    profile = await getProfile(params.id)
    age = calcAge(profile.birth_date)
  } catch {
    // Use defaults
  }

  const birthFormatted = profile.birth_date
    ? new Date(profile.birth_date).toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
      })
    : '—'

  return (
    <div>
      {/* Profile header */}
      <div className="bg-bg-card border border-bg-border rounded-xl p-6 mb-6">
        <div className="flex items-center gap-5">
          <Avatar profileId={params.id} name={profile.name} size="lg" />
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{profile.name}</h1>
            <p className="text-text-secondary mt-0.5">
              {birthFormatted}
              {age > 0 && (
                <span className="ml-2 text-text-muted">
                  ({age} {ageLabel(age)})
                </span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-bg-card border border-bg-border rounded-xl overflow-hidden">
        <ProfileTabs profileId={params.id} />
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}

function ageLabel(age: number): string {
  if (age === 1 || age === 21 || age === 31 || age === 41 || age === 51 || age === 61) return 'год'
  if ([2,3,4,22,23,24,32,33,34].includes(age)) return 'года'
  return 'лет'
}

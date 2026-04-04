import { AVATAR_COLORS, PROFILE_INITIALS } from '@/lib/mock'

interface AvatarProps {
  profileId: string
  name: string
  size?: 'sm' | 'md' | 'lg'
}

const sizeMap = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-14 h-14 text-lg',
}

export default function Avatar({ profileId, name, size = 'md' }: AvatarProps) {
  const color = AVATAR_COLORS[profileId] || '#6366f1'
  const initials = PROFILE_INITIALS[profileId] || name.slice(0, 2).toUpperCase()

  return (
    <div
      className={`${sizeMap[size]} rounded-full flex items-center justify-center font-semibold flex-shrink-0`}
      style={{ background: `${color}22`, color, border: `2px solid ${color}44` }}
    >
      {initials}
    </div>
  )
}

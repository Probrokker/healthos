import { AVATAR_COLORS } from "@/lib/mock"

interface AvatarProps {
  profileId: string
  name: string
  size?: "sm" | "md" | "lg"
}

const sizeMap = {
  sm: "w-8 h-8 text-xs",
  md: "w-10 h-10 text-sm",
  lg: "w-14 h-14 text-lg",
}

// Генерируем инициалы из имени — первые две буквы
function getInitials(name: string): string {
  const words = name.trim().split(" ")
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
}

// Цвет по ID или по хешу имени
function getColor(profileId: string, name: string): string {
  if (AVATAR_COLORS[profileId]) return AVATAR_COLORS[profileId]
  const colors = ["#6366f1","#ec4899","#f59e0b","#22c55e","#06b6d4","#e879f9","#f97316"]
  const hash = name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0)
  return colors[hash % colors.length]
}

export default function Avatar({ profileId, name, size = "md" }: AvatarProps) {
  const color = getColor(profileId, name)
  const initials = getInitials(name)

  return (
    <div
      className={`${sizeMap[size]} rounded-full flex items-center justify-center font-semibold flex-shrink-0`}
      style={{ background: `${color}22`, color, border: `2px solid ${color}44` }}
    >
      {initials}
    </div>
  )
}


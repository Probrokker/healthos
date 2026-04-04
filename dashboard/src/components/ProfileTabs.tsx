'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const tabs = [
  { label: 'Обзор', href: '' },
  { label: 'Анализы', href: '/labs' },
  { label: 'Динамика', href: '/trend' },
  { label: 'Рост', href: '/growth' },
]

export default function ProfileTabs({ profileId }: { profileId: string }) {
  const pathname = usePathname()
  const base = `/profile/${profileId}`

  return (
    <div className="border-b border-bg-border">
      <div className="flex gap-0 overflow-x-auto">
        {tabs.map((tab) => {
          const href = `${base}${tab.href}`
          const isActive = tab.href === '' ? pathname === base : pathname.startsWith(href)

          return (
            <Link
              key={tab.label}
              href={href}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-all whitespace-nowrap ${
                isActive
                  ? 'border-accent text-accent'
                  : 'border-transparent text-text-secondary hover:text-text-primary hover:border-bg-elevated'
              }`}
            >
              {tab.label}
            </Link>
          )
        })}
      </div>
    </div>
  )
}

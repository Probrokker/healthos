'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import Logo from './Logo'
import Avatar from './Avatar'
import { MOCK_PROFILES } from '@/lib/mock'

export default function Nav() {
  const pathname = usePathname()

  // Extract profile id from current path if any
  const profileMatch = pathname.match(/\/profile\/([^/]+)/)
  const currentProfileId = profileMatch ? profileMatch[1] : null

  return (
    <nav className="sticky top-0 z-50 border-b border-bg-border bg-bg-primary/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center gap-6 h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 flex-shrink-0">
            <Logo size={28} />
            <span className="font-semibold text-text-primary tracking-tight">
              Health<span className="text-accent">-OS</span>
            </span>
          </Link>

          <div className="w-px h-6 bg-bg-border" />

          {/* Family member selector */}
          <div className="flex items-center gap-1 overflow-x-auto pb-0 scrollbar-hide">
            {MOCK_PROFILES.map((profile) => {
              const isActive = currentProfileId === profile.id
              return (
                <Link
                  key={profile.id}
                  href={`/profile/${profile.id}`}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                    isActive
                      ? 'bg-accent/15 text-accent border border-accent/30'
                      : 'text-text-secondary hover:text-text-primary hover:bg-bg-card'
                  }`}
                >
                  <Avatar profileId={profile.id} name={profile.name} size="sm" />
                  <span>{profile.name}</span>
                </Link>
              )
            })}
          </div>

          <div className="ml-auto flex items-center gap-4">
            <Link
              href="/"
              className={`text-sm font-medium transition-colors ${
                pathname === '/'
                  ? 'text-accent'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              Обзор семьи
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}

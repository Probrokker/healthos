"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import Logo from "./Logo"
import Avatar from "./Avatar"
import { useTheme } from "./ThemeProvider"

interface NavProfile {
  id: string
  name: string
}

export default function Nav({ profiles }: { profiles: NavProfile[] }) {
  const pathname = usePathname()
  const { theme, toggle } = useTheme()

  const profileMatch = pathname.match(/\/profile\/([^/]+)/)
  const currentProfileId = profileMatch ? profileMatch[1] : null
  const isHome = pathname === "/"

  return (
    <nav style={{ borderBottom: "1px solid var(--bg-border)", backgroundColor: "var(--bg-primary)" }}
         className="sticky top-0 z-50 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-3 sm:px-6">
        <div className="flex items-center gap-2 sm:gap-4 h-14">

          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 flex-shrink-0">
            <Logo size={24} />
            <span className="font-semibold text-sm hidden sm:block" style={{ color: "var(--text-primary)" }}>
              Health<span style={{ color: "var(--accent)" }}>-OS</span>
            </span>
          </Link>

          <div className="w-px h-5 flex-shrink-0" style={{ backgroundColor: "var(--bg-border)" }} />

          {/* Family member pills — scrollable on mobile */}
          <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide flex-1 min-w-0">
            {/* Обзор — только иконка на мобиле */}
            <Link
              href="/"
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap flex-shrink-0"
              style={{
                backgroundColor: isHome ? "rgba(99,102,241,0.15)" : "transparent",
                color: isHome ? "var(--accent)" : "var(--text-secondary)",
                border: isHome ? "1px solid rgba(99,102,241,0.3)" : "1px solid transparent",
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
              </svg>
              <span className="hidden sm:inline">Обзор</span>
            </Link>

            {profiles.map((profile) => {
              const isActive = currentProfileId === String(profile.id)
              return (
                <Link
                  key={profile.id}
                  href={`/profile/${profile.id}`}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all whitespace-nowrap flex-shrink-0"
                  style={{
                    backgroundColor: isActive ? "rgba(99,102,241,0.15)" : "transparent",
                    color: isActive ? "var(--accent)" : "var(--text-secondary)",
                    border: isActive ? "1px solid rgba(99,102,241,0.3)" : "1px solid transparent",
                  }}
                >
                  <Avatar profileId={String(profile.id)} name={profile.name} size="sm" />
                  <span>{profile.name}</span>
                </Link>
              )
            })}
          </div>

          {/* Theme toggle */}
          <button
            onClick={toggle}
            title={theme === "dark" ? "Светлая тема" : "Тёмная тема"}
            className="w-8 h-8 rounded-lg flex items-center justify-center transition-all flex-shrink-0"
            style={{
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--bg-border)",
              color: "var(--text-secondary)",
            }}
          >
            {theme === "dark" ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="5"/>
                <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
            )}
          </button>

        </div>
      </div>
    </nav>
  )
}


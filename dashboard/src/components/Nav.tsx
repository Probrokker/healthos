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

  return (
    <nav style={{ borderBottom: "1px solid var(--bg-border)", backgroundColor: "var(--bg-primary)" }}
         className="sticky top-0 z-50 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center gap-6 h-16">

          <Link href="/" className="flex items-center gap-3 flex-shrink-0">
            <Logo size={28} />
            <span className="font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Health<span style={{ color: "var(--accent)" }}>-OS</span>
            </span>
          </Link>

          <div className="w-px h-6" style={{ backgroundColor: "var(--bg-border)" }} />

          <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
            {profiles.map((profile) => {
              const isActive = currentProfileId === String(profile.id)
              return (
                <Link
                  key={profile.id}
                  href={`/profile/${profile.id}`}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap"
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

          <div className="ml-auto flex items-center gap-3">
            <Link
              href="/"
              className="text-sm font-medium transition-colors"
              style={{ color: pathname === "/" ? "var(--accent)" : "var(--text-secondary)" }}
            >
              Обзор семьи
            </Link>

            <button
              onClick={toggle}
              title={theme === "dark" ? "Светлая тема" : "Тёмная тема"}
              className="w-9 h-9 rounded-lg flex items-center justify-center transition-all"
              style={{
                backgroundColor: "var(--bg-card)",
                border: "1px solid var(--bg-border)",
                color: "var(--text-secondary)",
              }}
            >
              {theme === "dark" ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="5"/>
                  <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                  <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}


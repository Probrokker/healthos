import type { Metadata } from "next"
import "./globals.css"
import Nav from "@/components/Nav"
import ThemeProvider from "@/components/ThemeProvider"
import { MOCK_PROFILES } from "@/lib/mock"

export const metadata: Metadata = {
  title: "Health-OS — Семейный медицинский дашборд",
  description: "Отслеживание здоровья семьи: анализы, визиты, рост, лекарства",
}

async function getNavProfiles() {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/profiles`,
      { cache: "no-store" }
    )
    if (!res.ok) throw new Error("API error")
    const data = await res.json()
    return data.map((p: { id: number; name: string; birthdate: string }) => ({
      id: String(p.id),
      name: p.name,
    }))
  } catch {
    return MOCK_PROFILES.map((p) => ({ id: p.id, name: p.name }))
  }
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const profiles = await getNavProfiles()

  return (
    <html lang="ru" suppressHydrationWarning>
      <body className="min-h-screen" style={{ backgroundColor: "var(--bg-primary)", color: "var(--text-primary)" }}>
        <ThemeProvider>
          <Nav profiles={profiles} />
          <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
            {children}
          </main>
        </ThemeProvider>
      </body>
    </html>
  )
}


import type { Metadata } from 'next'
import './globals.css'
import Nav from '@/components/Nav'

export const metadata: Metadata = {
  title: 'Health-OS — Семейный медицинский дашборд',
  description: 'Отслеживание здоровья семьи: анализы, визиты, рост, лекарства',
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><path d='M16 2L28 9V23L16 30L4 23V9L16 2Z' stroke='%236366f1' stroke-width='1.5' fill='none'/><rect x='14' y='8' width='4' height='16' rx='1.5' fill='%236366f1'/><rect x='8' y='14' width='16' height='4' rx='1.5' fill='%236366f1'/></svg>",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-bg-primary text-text-primary">
        <Nav />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
          {children}
        </main>
      </body>
    </html>
  )
}

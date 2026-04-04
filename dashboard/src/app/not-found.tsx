import Link from 'next/link'
import Logo from '@/components/Logo'

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center gap-6">
      <Logo size={48} />
      <div>
        <h1 className="text-4xl font-bold text-text-primary mb-2">404</h1>
        <p className="text-text-secondary text-lg">Страница не найдена</p>
      </div>
      <Link
        href="/"
        className="px-6 py-2.5 bg-accent/10 border border-accent/30 text-accent rounded-xl hover:bg-accent/20 transition-colors font-medium"
      >
        На главную
      </Link>
    </div>
  )
}

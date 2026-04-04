export default function LoadingSpinner({ label = 'Загрузка...' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 rounded-full border-2 border-bg-border" />
        <div className="absolute inset-0 rounded-full border-2 border-accent border-t-transparent animate-spin" />
      </div>
      <p className="text-text-secondary text-sm">{label}</p>
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-bg-card border border-bg-border rounded-xl p-6 animate-pulse">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-bg-elevated" />
        <div className="space-y-2">
          <div className="h-4 w-24 bg-bg-elevated rounded" />
          <div className="h-3 w-16 bg-bg-elevated rounded" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="space-y-1">
            <div className="h-3 w-full bg-bg-elevated rounded" />
            <div className="h-4 w-3/4 bg-bg-elevated rounded" />
          </div>
        ))}
      </div>
    </div>
  )
}

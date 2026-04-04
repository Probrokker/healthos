interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  accent?: boolean
  danger?: boolean
  warning?: boolean
}

export default function StatCard({ label, value, sub, accent, danger, warning }: StatCardProps) {
  const valueColor = danger
    ? 'text-red-400'
    : warning
    ? 'text-yellow-400'
    : accent
    ? 'text-accent'
    : 'text-text-primary'

  return (
    <div className="bg-bg-elevated/50 rounded-lg p-4 border border-bg-border">
      <p className="text-text-muted text-xs font-medium uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${valueColor}`}>{value}</p>
      {sub && <p className="text-text-secondary text-xs mt-0.5">{sub}</p>}
    </div>
  )
}

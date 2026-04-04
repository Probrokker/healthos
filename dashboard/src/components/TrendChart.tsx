'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
  Legend,
  Dot,
} from 'recharts'
import { TrendPoint, formatDate } from '@/lib/api'

interface TrendChartProps {
  data: TrendPoint[]
  markerName: string
}

function CustomDot(props: any) {
  const { cx, cy, payload } = props
  const color =
    payload.status === 'critical' || payload.status === 'critical_low'
      ? '#ef4444'
      : payload.status === 'high' || payload.status === 'low'
      ? '#f59e0b'
      : '#22c55e'

  return (
    <circle
      key={`dot-${cx}-${cy}`}
      cx={cx}
      cy={cy}
      r={5}
      fill={color}
      stroke="#0f1117"
      strokeWidth={2}
    />
  )
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload as TrendPoint
  const statusColors: Record<string, string> = {
    normal: '#22c55e',
    high: '#f59e0b',
    low: '#f59e0b',
    critical: '#ef4444',
    critical_low: '#ef4444',
  }
  const statusLabels: Record<string, string> = {
    normal: 'Норма',
    high: 'Повышен',
    low: 'Понижен',
    critical: 'Критично',
    critical_low: 'Крит. низкий',
  }
  const color = statusColors[d.status] || '#8b8fa8'

  return (
    <div className="bg-bg-card border border-bg-border rounded-xl p-3 shadow-xl text-sm">
      <p className="text-text-muted mb-2">{formatDate(d.date)}</p>
      <p className="font-bold text-text-primary text-lg">
        {d.value} <span className="text-text-muted text-sm font-normal">{d.unit}</span>
      </p>
      {d.ref_min !== undefined && d.ref_max !== undefined && (
        <p className="text-text-muted text-xs mt-1">
          Референс: {d.ref_min} – {d.ref_max} {d.unit}
        </p>
      )}
      <p className="mt-2 text-xs font-medium" style={{ color }}>
        {statusLabels[d.status] || d.status}
      </p>
    </div>
  )
}

export default function TrendChart({ data, markerName }: TrendChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-text-muted">
        Нет данных для отображения
      </div>
    )
  }

  // Get ref range from first point that has it
  const refPoint = data.find((d) => d.ref_min !== undefined && d.ref_max !== undefined)
  const refMin = refPoint?.ref_min
  const refMax = refPoint?.ref_max
  const unit = data[0]?.unit || ''

  // Compute Y domain with padding
  const values = data.map((d) => d.value)
  const allValues = [...values, ...(refMin !== undefined ? [refMin] : []), ...(refMax !== undefined ? [refMax] : [])]
  const minVal = Math.min(...allValues)
  const maxVal = Math.max(...allValues)
  const pad = (maxVal - minVal) * 0.2 || 1
  const yMin = Math.max(0, minVal - pad)
  const yMax = maxVal + pad

  const chartData = data.map((d) => ({
    ...d,
    dateLabel: new Date(d.date).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: '2-digit' }),
  }))

  return (
    <div>
      {/* Reference range indicators */}
      {refMin !== undefined && refMax !== undefined && (
        <div className="flex items-center gap-6 mb-4 text-xs text-text-secondary">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm" style={{ background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(34,197,94,0.3)' }} />
            Норма: {refMin}–{refMax} {unit}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-400" />
            Критично
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-yellow-400" />
            Отклонение
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-green-400" />
            Норма
          </span>
        </div>
      )}

      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(42,45,62,0.8)" />
          <XAxis
            dataKey="dateLabel"
            tick={{ fill: '#8b8fa8', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#2a2d3e' }}
          />
          <YAxis
            domain={[yMin, yMax]}
            tick={{ fill: '#8b8fa8', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => v.toFixed(1)}
            width={50}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Reference range shaded band */}
          {refMin !== undefined && refMax !== undefined && (
            <ReferenceArea
              y1={refMin}
              y2={refMax}
              fill="rgba(34,197,94,0.08)"
              stroke="rgba(34,197,94,0.2)"
              strokeDasharray="4 4"
            />
          )}

          {/* Ref lines */}
          {refMin !== undefined && (
            <ReferenceLine
              y={refMin}
              stroke="rgba(34,197,94,0.4)"
              strokeDasharray="4 4"
              label={{ value: `мин ${refMin}`, fill: '#22c55e', fontSize: 10, position: 'insideBottomLeft' }}
            />
          )}
          {refMax !== undefined && (
            <ReferenceLine
              y={refMax}
              stroke="rgba(34,197,94,0.4)"
              strokeDasharray="4 4"
              label={{ value: `макс ${refMax}`, fill: '#22c55e', fontSize: 10, position: 'insideTopLeft' }}
            />
          )}

          <Line
            type="monotone"
            dataKey="value"
            name={markerName}
            stroke="#6366f1"
            strokeWidth={2.5}
            dot={<CustomDot />}
            activeDot={{ r: 7, fill: '#6366f1', stroke: '#0f1117', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

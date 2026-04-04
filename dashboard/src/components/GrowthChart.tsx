'use client'

import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { GrowthRecord, formatDate } from '@/lib/api'

interface GrowthChartProps {
  data: GrowthRecord[]
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload as GrowthRecord & { dateLabel: string }

  return (
    <div className="bg-bg-card border border-bg-border rounded-xl p-3 shadow-xl text-sm min-w-[160px]">
      <p className="text-text-muted mb-2 text-xs">{formatDate(d.date)}</p>
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color }} />
            <span className="text-text-secondary text-xs">{p.name}</span>
          </div>
          <span className="font-semibold text-text-primary">
            {p.value} {p.name === 'Рост (см)' ? 'см' : 'кг'}
          </span>
        </div>
      ))}
      {d.bmi !== undefined && (
        <div className="mt-2 pt-2 border-t border-bg-border">
          <span className="text-text-muted text-xs">ИМТ: </span>
          <span className="text-text-primary text-xs font-semibold">{d.bmi?.toFixed(1)}</span>
        </div>
      )}
    </div>
  )
}

export default function GrowthChart({ data }: GrowthChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-text-muted">
        Нет данных для отображения
      </div>
    )
  }

  const chartData = data.map((d) => ({
    ...d,
    dateLabel: new Date(d.date).toLocaleDateString('ru-RU', { month: 'short', year: '2-digit' }),
  }))

  const heights = data.map((d) => d.height_cm).filter(Boolean)
  const weights = data.map((d) => d.weight_kg).filter(Boolean)

  const heightMin = Math.min(...heights) - 5
  const heightMax = Math.max(...heights) + 5
  const weightMin = Math.max(0, Math.min(...weights) - 2)
  const weightMax = Math.max(...weights) + 2

  return (
    <div>
      {/* Legend */}
      <div className="flex items-center gap-6 mb-4 text-xs text-text-secondary">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 rounded" style={{ background: '#6366f1' }} />
          <span className="w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-b-[6px]" style={{ borderBottomColor: '#6366f1' }} />
          Рост (см) — левая ось
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 rounded" style={{ background: '#22c55e' }} />
          Вес (кг) — правая ось
        </span>
      </div>

      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 60, left: 0, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(42,45,62,0.8)" />
          <XAxis
            dataKey="dateLabel"
            tick={{ fill: '#8b8fa8', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#2a2d3e' }}
          />
          {/* Left Y axis — height */}
          <YAxis
            yAxisId="height"
            orientation="left"
            domain={[heightMin, heightMax]}
            tick={{ fill: '#6366f1', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${v}`}
            width={45}
            label={{
              value: 'см',
              angle: -90,
              position: 'insideLeft',
              fill: '#6366f1',
              fontSize: 11,
              offset: 10,
            }}
          />
          {/* Right Y axis — weight */}
          <YAxis
            yAxisId="weight"
            orientation="right"
            domain={[weightMin, weightMax]}
            tick={{ fill: '#22c55e', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${v}`}
            width={45}
            label={{
              value: 'кг',
              angle: 90,
              position: 'insideRight',
              fill: '#22c55e',
              fontSize: 11,
              offset: 10,
            }}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Height line */}
          <Line
            yAxisId="height"
            type="monotone"
            dataKey="height_cm"
            name="Рост (см)"
            stroke="#6366f1"
            strokeWidth={2.5}
            dot={{ fill: '#6366f1', stroke: '#0f1117', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 7, fill: '#6366f1', stroke: '#0f1117', strokeWidth: 2 }}
          />
          {/* Weight line */}
          <Line
            yAxisId="weight"
            type="monotone"
            dataKey="weight_kg"
            name="Вес (кг)"
            stroke="#22c55e"
            strokeWidth={2.5}
            strokeDasharray="6 3"
            dot={{ fill: '#22c55e', stroke: '#0f1117', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 7, fill: '#22c55e', stroke: '#0f1117', strokeWidth: 2 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

interface ErrorCardProps {
  title?: string
  message?: string
  retry?: () => void
}

export default function ErrorCard({
  title = 'Ошибка загрузки',
  message = 'Не удалось получить данные. Проверьте подключение к API.',
  retry,
}: ErrorCardProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
            stroke="#ef4444"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <div className="text-center">
        <h3 className="text-text-primary font-semibold mb-1">{title}</h3>
        <p className="text-text-secondary text-sm max-w-xs">{message}</p>
      </div>
      {retry && (
        <button
          onClick={retry}
          className="px-4 py-2 rounded-lg bg-accent/10 text-accent border border-accent/30 text-sm hover:bg-accent/20 transition-colors"
        >
          Повторить
        </button>
      )}
    </div>
  )
}
